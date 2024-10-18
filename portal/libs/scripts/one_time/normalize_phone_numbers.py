import logging
from tqdm import tqdm

from thedaily.models import Subscriber


phone_fields = {Subscriber: ["phone"]}


def sql_replacements(exclude=[]):
    blank_patterns = ['-01 x+']
    for model, fields in phone_fields.items():
        if model in exclude:
            continue
        for field in fields:
            where = ' OR '.join([f"{field} REGEXP '^{pattern}$'" for pattern in blank_patterns])
            print(f"UPDATE {model._meta.db_table} SET {field} = '' WHERE {where};\n")
            set_str = f"{field}=TRIM(SUBSTRING_INDEX({field}, '/', 1))"
            print(f"UPDATE {model._meta.db_table} SET {set_str} WHERE {field} LIKE '%/%';\n")


def normalize_phone_numbers(extra=[], filters={}, dry_run=False):
    logging.basicConfig(
        filename='/tmp/normalize_subscribers_phone_numbers.log',
        level=logging.INFO,
        filemode='w',
        format='%(levelname)s: %(message)s',
    )
    phone_fields.update(extra)

    for model, fields in phone_fields.items():
        model_name, model_objects = model.__name__, model.objects

        filter = filters.get(model_name)
        if filter:
            model_objects = model_objects.filter(**filter)

        model_objects = model_objects.exclude(**{f: "" for f in fields})

        saved, skipped, already_normalized_with_invalid, already_normalized_no_invalid = 0, 0, 0, 0
        with_all_invalid, with_error, total = 0, 0, model_objects.count()
        if total:
            logging.info(f"{model_name} objects to normalize: {total}")
        else:
            continue

        for obj in tqdm(model_objects.iterator(), total=total, desc=f"Normalizing {model_name}"):

            need_save = False
            has_valid = False
            invalids = []

            for field in fields:
                value = getattr(obj, field)
                if value:
                    if value.is_valid():
                        has_valid = True
                        need_save = need_save or value.raw_input != value.as_e164
                    else:
                        invalids.append((field, value))

            has_invalid = bool(invalids)
            if has_invalid:
                invalids_str = ", ".join([f"{field}: {value}" for field, value in invalids])
                logging.warning(f"Invalid numbers for {model_name} pk {obj.pk}: {invalids_str}")

            if need_save:
                if dry_run:
                    skipped += 1
                else:
                    try:
                        obj.updatefromcrm = True
                        obj.save()
                        saved += 1
                    except Exception as e:
                        logging.error(f"Failed to normalize number for {model_name} pk {obj.pk}: {e}")
                        with_error += 1
            else:
                if has_valid:
                    if has_invalid:
                        already_normalized_with_invalid += 1
                    else:
                        already_normalized_no_invalid += 1
                else:
                    with_all_invalid += 1

        logging.info(f"{saved} Saved")
        logging.info("Not saved:")
        if dry_run:
            logging.info(f"  {skipped} skipped (dry run)")
        else:
            logging.info(f"  {with_error} error saving\n")
        logging.info(f"  {already_normalized_no_invalid} already normalized with all non-blank valid")
        logging.info(f"  {already_normalized_with_invalid} already normalized non-blanks with one+ invalid left")
        logging.info(f"  {with_all_invalid} all non-blank are invalid")


if __name__ == "__main__":
    normalize_phone_numbers()
