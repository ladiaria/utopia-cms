# -*- coding: utf-8 -*-
"""
Dump last N rows (by id) of photologue_photo and related photologue_ladiaria_photoextended
to SQL files, and pack all involved image files into a .tar for restore by raw SQL.

Usage (from portal directory with the virtual environment activated):
  ./manage.py runscript libs.scripts.dump_photologue_last_n --script-args N [OUT_DIR] [TAR_NAME]

Output:
  - photologue_photo.sql, photologue_ladiaria_photoextended.sql (in out_dir)
  - dump_photologue_<timestamp>.tar: single archive with all image files (photo.image, extended.square_version,
    extended.last_original_uploaded; paths as in MEDIA).

Restore (MariaDB/MySQL; assumes agency and photographer already loaded, no FK issues):
  1. Run: mysql ... < photologue_photo.sql && mysql ... < photologue_ladiaria_photoextended.sql
  2. Extract the image files into MEDIA_ROOT (they keep their path in the tar).
"""

import argparse
import os
import sys
import tarfile
from datetime import date, datetime
from decimal import Decimal

from django.conf import settings
from django.db import connection


def mysql_escape_value(val):
    """Format a single value for MariaDB/MySQL INSERT."""
    if val is None:
        return "NULL"
    if isinstance(val, (int, float, Decimal)):
        return str(val) if not isinstance(val, float) or not (val != val) else "NULL"  # NaN
    if isinstance(val, (datetime, date)):
        s = str(val)
        return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"
    if isinstance(val, bool):
        return "1" if val else "0"
    if isinstance(val, bytes):
        return "0x" + val.hex()
    s = str(val)
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def row_to_values(row, col_names):
    return ", ".join(mysql_escape_value(row[i]) for i in range(len(col_names)))


def dump_table(cursor, table, id_column, ids, order_col="id"):
    """Return (single multi-row INSERT statement, row count). MariaDB/MySQL compatible."""
    if not ids:
        return "", 0
    placeholders = ", ".join("%s" for _ in ids)
    cursor.execute(
        "SELECT * FROM `%s` WHERE `%s` IN (%s) ORDER BY `%s`"
        % (table, id_column, placeholders, order_col),
        list(ids),
    )
    col_names = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    if not rows:
        return "", 0
    cols = ", ".join("`%s`" % c for c in col_names)
    values_list = ", ".join("(%s)" % row_to_values(row, col_names) for row in rows)
    stmt = "INSERT INTO `%s` (%s) VALUES %s;\n" % (table, cols, values_list)
    return stmt, len(rows)


def collect_image_paths(cursor, photo_ids, media_root):
    """Return set of (absolute_path, arcname) for files to add to tar (arcname = path under MEDIA)."""
    paths = set()
    placeholders = ", ".join("%s" for _ in photo_ids)
    cursor.execute(
        "SELECT id, image FROM photologue_photo WHERE id IN (%s)" % placeholders,
        list(photo_ids),
    )
    for row in cursor.fetchall():
        name = row[1]
        if name:
            abs_path = os.path.join(media_root, name)
            if os.path.isfile(abs_path):
                paths.add((abs_path, name))
    cursor.execute(
        "SELECT square_version, last_original_uploaded "
        "FROM photologue_ladiaria_photoextended WHERE image_id IN (%s)" % placeholders,
        list(photo_ids),
    )
    for row in cursor.fetchall():
        for name in (row[0], row[1]):
            if name:
                abs_path = os.path.join(media_root, name)
                if os.path.isfile(abs_path):
                    paths.add((abs_path, name))
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("n", type=int, help="Last N rows by id (photologue_photo)")
    parser.add_argument("--out-dir", default=None, help="Output directory (default: cwd)")
    parser.add_argument("--tar-name", default=None, help="Final tar name (default: dump_photologue_<timestamp>.tar)")
    args = parser.parse_args()
    out_dir = args.out_dir or os.getcwd()
    os.makedirs(out_dir, exist_ok=True)
    media_root = getattr(settings, "MEDIA_ROOT", None) or os.path.join(settings.PROJECT_ABSOLUTE_DIR, "media")
    if not os.path.isdir(media_root):
        print("Warning: MEDIA_ROOT not found:", media_root, file=sys.stderr)

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT id FROM photologue_photo ORDER BY id DESC LIMIT %s",
            [args.n],
        )
        photo_ids = [r[0] for r in cursor.fetchall()]
        if not photo_ids:
            print("No rows in photologue_photo.", file=sys.stderr)
            return 1

        stmt_photo, n_photo = dump_table(cursor, "photologue_photo", "id", photo_ids)
        sql_photo_path = os.path.join(out_dir, "photologue_photo.sql")
        with open(sql_photo_path, "w", encoding="utf-8") as f:
            f.write("-- photologue_photo (last %s by id)\n" % args.n)
            f.write(stmt_photo)
        print("Wrote %s (%s rows)" % (sql_photo_path, n_photo))

        stmt_ext, n_ext = dump_table(
            cursor, "photologue_ladiaria_photoextended", "image_id", photo_ids, order_col="id"
        )
        sql_ext_path = os.path.join(out_dir, "photologue_ladiaria_photoextended.sql")
        with open(sql_ext_path, "w", encoding="utf-8") as f:
            f.write("-- photologue_ladiaria_photoextended (related to last %s photos)\n" % args.n)
            f.write(stmt_ext)
        print("Wrote %s (%s rows)" % (sql_ext_path, n_ext))

        image_paths = collect_image_paths(cursor, photo_ids, media_root)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_tar_name = args.tar_name or ("dump_photologue_%s.tar" % stamp)
    final_tar_path = os.path.join(out_dir, final_tar_name)
    with tarfile.open(final_tar_path, "w") as tar:
        for abs_path, arcname in sorted(image_paths, key=lambda x: x[1]):
            tar.add(abs_path, arcname=arcname)
    print("Wrote %s (%s images)" % (final_tar_path, len(image_paths)))
    return 0


def run(*args):
    """Entry point for manage.py runscript. Positional: n, [out_dir], [tar_name]."""
    argv = ["dump_photologue_last_n", str(args[0])] if args else ["dump_photologue_last_n", "10"]
    if len(args) >= 2 and args[1]:
        argv.extend(["--out-dir", args[1]])
    if len(args) >= 3 and args[2]:
        argv.extend(["--tar-name", args[2]])
    orig = sys.argv
    sys.argv = argv
    try:
        return main()
    finally:
        sys.argv = orig
