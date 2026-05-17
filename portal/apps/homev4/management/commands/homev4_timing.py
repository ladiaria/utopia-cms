import re
from django.core.management.base import BaseCommand

LOG_PATH = "/var/log/uwsgi/ldsocial.log"
TIMING_RE = re.compile(r"active_layout timing: ([\d.]+) ms \(user_auth=(\w+)\)")
# Captures the text after "WARNING:homev4:" for build and phase lines, excluding the timing summary.
DETAIL_RE = re.compile(r"WARNING:homev4:(  build: \w+=[\d.]+ ms|active_layout [\w_]+: [\d.]+ ms)")


class Command(BaseCommand):
    help = "Show homev4 active_layout response times from the uwsgi log."

    def add_arguments(self, parser):
        parser.add_argument("-n", type=int, default=10, help="Number of requests to show (default: 10)")
        parser.add_argument("-f", "--follow", action="store_true", help="Follow log in real time (Ctrl+C to stop)")
        parser.add_argument("--detail", action="store_true", help="Show per-block breakdown for each request")
        parser.add_argument("--log", default=LOG_PATH, help=f"Log file path (default: {LOG_PATH})")

    def handle(self, *args, **options):
        if options["follow"]:
            self._follow(options)
        else:
            self._tail(options)

    def _tail(self, options):
        try:
            with open(options["log"]) as f:
                lines = f.readlines()
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Log not found: {options['log']}"))
            return

        requests = []
        current_blocks = []
        for line in lines:
            m = TIMING_RE.search(line)
            if m:
                requests.append({
                    "ms": float(m.group(1)),
                    "auth": m.group(2) == "True",
                    "blocks": current_blocks[:],
                })
                current_blocks = []
                continue
            d = DETAIL_RE.search(line)
            if d:
                current_blocks.append(d.group(1))

        shown = requests[-options["n"]:]
        if not shown:
            self.stdout.write("No timing entries found.")
            return

        self.stdout.write(f"\nLast {len(shown)} requests:\n")
        for r in shown:
            auth_label = self.style.SUCCESS("auth") if r["auth"] else "anon"
            ms = r["ms"]
            color = self.style.ERROR if ms > 800 else (self.style.WARNING if ms > 500 else self.style.SUCCESS)
            self.stdout.write(f"  {color(f'{ms:.1f} ms')}  [{auth_label}]")
            if options["detail"]:
                for b in r["blocks"]:
                    self.stdout.write(f"    {b}")

        times = [r["ms"] for r in shown]
        self.stdout.write(f"\n  avg={sum(times)/len(times):.1f} ms  min={min(times):.1f} ms  max={max(times):.1f} ms\n")

    def _follow(self, options):
        import subprocess
        self.stdout.write(f"Following {options['log']} — Ctrl+C to stop\n")
        try:
            proc = subprocess.Popen(
                ["tail", "-f", options["log"]],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
            current_blocks = []
            for line in proc.stdout:
                m = TIMING_RE.search(line)
                if m:
                    ms = float(m.group(1))
                    auth_label = "auth" if m.group(2) == "True" else "anon"
                    color = self.style.ERROR if ms > 800 else (self.style.WARNING if ms > 500 else self.style.SUCCESS)
                    self.stdout.write(f"  {color(f'{ms:.1f} ms')}  [{auth_label}]")
                    if options["detail"] and current_blocks:
                        for b in current_blocks:
                            self.stdout.write(f"    {b}")
                    current_blocks = []
                    continue
                d = DETAIL_RE.search(line)
                if d:
                    current_blocks.append(d.group(1))
        except KeyboardInterrupt:
            proc.terminate()
