import json
import re
import shutil
from pathlib import Path
from PIL import Image

SRC = Path("packs_src")
ASSETS = Path("Android/app/src/main/assets")
BUILD_GRADLE = Path("Android/app/build.gradle")
STRINGS_XML = Path("Android/app/src/main/res/values/strings.xml")

APP_ID = "com.tuusuario.stickers"
APP_NAME = "Stickers Telegram"
PUBLISHER = "Dave Kidoh"

def sanitize_identifier(text: str) -> str:
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.- ")
    cleaned = "".join(ch if ch in allowed else "_" for ch in text)
    return cleaned[:120]

def is_animated_webp(path: Path) -> bool:
    with Image.open(path) as im:
        return bool(getattr(im, "is_animated", False) or getattr(im, "n_frames", 1) > 1)

def make_tray_icon(src_webp: Path, dest_png: Path):
    with Image.open(src_webp) as im:
        if getattr(im, "is_animated", False):
            im.seek(0)
        im = im.convert("RGBA")
        im.thumbnail((96, 96))
        canvas = Image.new("RGBA", (96, 96), (0, 0, 0, 0))
        x = (96 - im.width) // 2
        y = (96 - im.height) // 2
        canvas.paste(im, (x, y), im)
        canvas.save(dest_png, format="PNG", optimize=True)

def patch_build_files():
    gradle_text = BUILD_GRADLE.read_text(encoding="utf-8")
    gradle_text = re.sub(
        r'applicationId\s+"[^"]+"',
        f'applicationId "{APP_ID}"',
        gradle_text,
        count=1
    )
    BUILD_GRADLE.write_text(gradle_text, encoding="utf-8")

    strings_text = STRINGS_XML.read_text(encoding="utf-8")
    strings_text = re.sub(
        r'(<string name="app_name">)(.*?)(</string>)',
        rf'\1{APP_NAME}\3',
        strings_text,
        count=1
    )
    STRINGS_XML.write_text(strings_text, encoding="utf-8")

def main():
    if not SRC.exists():
        raise SystemExit("No existe packs_src/")

    # limpiar assets previos
    ASSETS.mkdir(parents=True, exist_ok=True)
    for item in ASSETS.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        elif item.name == "contents.json":
            item.unlink()

    pack_dirs = sorted([p for p in SRC.iterdir() if p.is_dir()])
    if not pack_dirs:
        raise SystemExit("No hay carpetas dentro de packs_src/")

    sticker_packs = []

    for idx, pack_dir in enumerate(pack_dirs, start=1):
        files = sorted(pack_dir.glob("*.webp"))
        if len(files) < 3 or len(files) > 30:
            raise SystemExit(f"{pack_dir.name}: debe tener entre 3 y 30 stickers y tiene {len(files)}")

        animated_flags = [is_animated_webp(f) for f in files]
        if len(set(animated_flags)) > 1:
            raise SystemExit(f"{pack_dir.name}: mezcla stickers estáticos y animados")

        folder = ASSETS / str(idx)
        folder.mkdir(parents=True, exist_ok=True)

        for src in files:
            shutil.copy2(src, folder / src.name)

        tray_icon = folder / "tray_icon.png"
        make_tray_icon(files[0], tray_icon)

        stickers = []
        for src in files:
            stickers.append({
                "image_file": src.name,
                "emojis": ["🙂"],
                "accessibility_text": src.stem[:120]
            })

        sticker_packs.append({
            "identifier": str(idx),
            "name": pack_dir.name,
            "publisher": PUBLISHER,
            "tray_image_file": "tray_icon.png",
            "image_data_version": "1",
            "animated_sticker_pack": bool(animated_flags[0]),
            "publisher_website": "",
            "privacy_policy_website": "",
            "license_agreement_website": "",
            "stickers": stickers
        })

    contents = {"sticker_packs": sticker_packs}
    (ASSETS / "contents.json").write_text(
        json.dumps(contents, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    patch_build_files()

    print(json.dumps({
        "app_id": APP_ID,
        "app_name": APP_NAME,
        "packs": [p["name"] for p in sticker_packs]
    }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
