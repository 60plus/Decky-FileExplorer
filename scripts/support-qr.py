"""Rebuild checked-in QR assets (development only: qrcode==8.2, Pillow).

Run manually when an address changes; not part of the plugin build or runtime.

The payloads come from the same JSON used by the UI and clipboard. Encode only
the URL/address, without an amount or extra wallet parameters. Four transparent
modules around the code provide the quiet zone on the UI's pale card.
"""
import json
from pathlib import Path

import qrcode

ROOT = Path(__file__).resolve().parents[1]
destinations = json.loads((ROOT / "src/support.json").read_text(encoding="utf-8"))
output = ROOT / "images/support"
output.mkdir(parents=True, exist_ok=True)
for name, value in destinations.items():
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                         box_size=8, border=4)
    code.add_data(value, optimize=0)
    code.make(fit=True)
    code.make_image(fill_color="#17212b", back_color="transparent").save(
        output / f"{name}-qr.png")
    print(f"{name}: {code.modules_count} x {code.modules_count} modules")
