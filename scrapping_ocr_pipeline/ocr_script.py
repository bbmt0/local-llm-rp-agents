import os
import json
from typing import List, Dict, Any
from PIL import Image, ImageFilter, ImageOps
import pytesseract
from tkinter import Tk, filedialog
from config import IMAGES_DIR
import shutil



def choose_folder(start_dir: str = IMAGES_DIR) -> str:
    """Ouvre une fenêtre pour choisir un dossier."""
    root = Tk()
    root.withdraw()  # on cache la fenêtre principale Tk
    folder = filedialog.askdirectory(
        initialdir=start_dir,
        title="Choisis le dossier contenant les images"
    )
    root.destroy()
    return folder


def list_image_files(folder: str) -> List[str]:
    files: List[str] = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        lower = name.lower()
        if lower.endswith(".png") or lower.endswith(".jpg") or lower.endswith(".jpeg"):
            files.append(path)
    return sorted(files)


def preprocess_image(image_path: str) -> Image.Image:
    """
    Pré-traitement pour screen GTA :
    - crop la zone du haut (zone de chat)
    - niveaux de gris
    - upscale x3
    - léger filtre anti-bruit
    - autocontrast
    - binarisation (noir/blanc)
    """
    img = Image.open(image_path)
    w, h = img.size

    # 1) on ne garde que le haut de l'image (zone de texte)
    # tu peux ajuster 0.30 -> 0.25 / 0.35 suivant tes screens
    chat_height = int(h * 0.30)
    img = img.crop((0, 0, w, chat_height))

    # 2) niveaux de gris
    img = img.convert("L")

    # 3) upscale x3 pour aider Tesseract
    scale = 4
    img = img.resize((w * scale, chat_height * scale), Image.Resampling.LANCZOS)

    # 4) léger filtre pour réduire le bruit
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # 5) augmenter contraste
    img = ImageOps.autocontrast(img)

    # 6) binarisation simple
    threshold = 140  # à ajuster, 140–170 en général
    img = img.point(lambda x: 255 if x > threshold else 0)

    return img




def ocr_image(image: Image.Image, lang: str = "fra+eng") -> str:
    """Applique Tesseract sur une image PIL et renvoie le texte."""
    text = pytesseract.image_to_string(image, lang=lang)
    return text.strip()


def test_first_image(folder: str) -> None:
    """Fait l'OCR uniquement sur la première image du dossier et affiche le résultat."""
    images = list_image_files(folder)
    if not images:
        print(f"Aucune image trouvée dans {folder}")
        return

    first = images[1]
    print(f"🖼  Test OCR sur la première image : {first}")

    img = preprocess_image(first)
    img.save("debug_preprocessed.png")

    text = ocr_image(img, lang="fra+eng")

    print("\n===== TEXTE OCR (aperçu) =====")
    print(text)
    print("===== FIN APERÇU =====\n")


def run_ocr_on_folder(folder: str) -> None:
    """
    Traite TOUTES les images du dossier et écrit les résultats dans un JSONL
    à côté (dossier 'interim' créé à côté du dossier parent).
    """
    images = list_image_files(folder)
    if not images:
        print(f"Aucune image trouvée dans {folder}")
        return

    print(f"{len(images)} images trouvées dans {folder}")

    base_dir = os.path.abspath(os.path.join(folder, "..", ".."))  # on remonte depuis raw/images/xxx
    interim_dir = os.path.join(base_dir, "interim")
    os.makedirs(interim_dir, exist_ok=True)

    folder_name = os.path.basename(folder.rstrip("/"))
    output_path = os.path.join(interim_dir, f"{folder_name}_ocr.jsonl")

    with open(output_path, "w", encoding="utf-8") as f_out:
        for img_path in images:
            try:
                img = preprocess_image(img_path)
                text = ocr_image(img, lang="fra+eng")
                record: Dict[str, Any] = {
                    "folder": folder_name,
                    "image_path": img_path,
                    "text": text,
                }
                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")
                print(f"OCR OK : {img_path}")
            except Exception as e:
                print(f"Erreur OCR sur {img_path} : {e}")

    print(f"\nOCR terminé. Résultat enregistré dans : {output_path}")


if __name__ == "__main__":
    print("Sélectionne le dossier contenant les images (ex: data/raw/images/young_swervin_locs)")
    folder = choose_folder()

    if not folder:
        print("Aucun dossier sélectionné, on arrête.")
    else:
        print(f"\nDossier choisi : {folder}\n")

        # 1) Test sur la première image
        test_first_image(folder)

        # 2) Demander confirmation avant de tout lancer
        confirm = input("Lancer l'OCR sur TOUTES les images de ce dossier ? (o/n) : ").strip().lower()
        if confirm == "o":
            run_ocr_on_folder(folder)
        else:
            print("OCR global annulé.")
