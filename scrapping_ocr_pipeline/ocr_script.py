import os
import json
from typing import List, Dict, Any
from PIL import Image, ImageFilter, ImageOps
import pytesseract
from tkinter import Tk, filedialog
from config import IMAGES_DIR
import shutil  # encore utile si tu veux gérer tesseract_cmd autrement


# -------------------------------------------------------
# Utils sélection dossier / fichiers
# -------------------------------------------------------

def choose_folder(start_dir: str = IMAGES_DIR) -> str:
    root = Tk()
    root.withdraw()
    folder = filedialog.askdirectory(
        initialdir=start_dir,
        title="Choisis le dossier"
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


# -------------------------------------------------------
# Pré-traitement image / OCR
# -------------------------------------------------------

def preprocess_image(image_path: str) -> Image.Image:
    """
    Pré-traitement pour screen GTA :
    - crop la zone du haut (zone de chat)
    - niveaux de gris
    - upscale x4
    - léger filtre anti-bruit
    - autocontrast
    - binarisation (noir/blanc)
    """
    img = Image.open(image_path)
    w, h = img.size

    # 1) on ne garde que le haut de l'image (zone de texte)
    chat_height = int(h * 0.30)
    img = img.crop((0, 0, w, chat_height))

    # 2) niveaux de gris
    img = img.convert("L")

    # 3) upscale x4 pour aider Tesseract
    scale = 4
    img = img.resize((w * scale, chat_height * scale), Image.Resampling.LANCZOS)

    # 4) léger filtre pour réduire le bruit
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # 5) augmenter contraste
    img = ImageOps.autocontrast(img)

    # 6) binarisation simple
    threshold = 140  # à ajuster
    img = img.point(lambda x: 255 if x > threshold else 0)

    return img


def ocr_image(image: Image.Image, lang: str = "fra+eng") -> str:
    """Applique Tesseract sur une image PIL et renvoie le texte."""
    # Tu peux ajouter un config psm/oem ici si tu veux
    text = pytesseract.image_to_string(image, lang=lang)
    return text.strip()


# -------------------------------------------------------
# Index des images (sortie du scraper)
# -------------------------------------------------------

def load_image_index_for_folder(folder: str) -> Dict[str, Dict[str, Any]]:
    """
    Charge le fichier <topic_folder>_images_index.jsonl et renvoie
    un dict filename -> metadata.
    """
    base_dir = os.path.abspath(os.path.join(folder, "..", ".."))  # data/raw/images/<topic>/ -> data/
    interm_dir = os.path.join(base_dir, "interm")

    topic_folder = os.path.basename(folder.rstrip("/"))
    index_path = os.path.join(interm_dir, f"{topic_folder}_images_index.jsonl")

    if not os.path.exists(index_path):
        raise FileNotFoundError(f"Index images introuvable : {index_path}")

    mapping: Dict[str, Dict[str, Any]] = {}
    with open(index_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            filename = rec.get("filename")
            if not filename:
                continue
            mapping[filename] = rec

    print(f"Index images chargé : {len(mapping)} entrées depuis {index_path}")
    return mapping


# -------------------------------------------------------
# Debug : test sur la première image
# -------------------------------------------------------

def test_first_image(folder: str) -> None:
    """Fait l'OCR uniquement sur la première image du dossier et affiche le résultat."""
    images = list_image_files(folder)
    if not images:
        print(f"Aucune image trouvée dans {folder}")
        return

    first = images[2]
    print(f"🖼  Test OCR sur la première image : {first}")

    img = preprocess_image(first)
    img.save("test_first_picture.png")

    text = ocr_image(img, lang="fra+eng")

    print("\n===== TEXTE OCR (aperçu) =====")
    print(text)
    print("===== FIN APERÇU =====\n")


# -------------------------------------------------------
# OCR global + regroupement par scène (page, post_index)
# -------------------------------------------------------

def run_ocr_on_folder(folder: str) -> None:
    """
    Traite TOUTES les images du dossier et écrit deux JSONL :
    1) <topic>_ocr_per_image.jsonl : un enregistrement par image
    2) <topic>_ocr_scenes.jsonl    : un enregistrement par scène (page + post_index)
    """
    images = list_image_files(folder)
    if not images:
        print(f"Aucune image trouvée dans {folder}")
        return

    print(f"{len(images)} images trouvées dans {folder}")

    # base_dir = data/  (si folder = data/raw/images/<topic>)
    base_dir = os.path.abspath(os.path.join(folder, "..", ".."))
    interm_dir = os.path.join(base_dir, "interm")
    os.makedirs(interm_dir, exist_ok=True)

    folder_name = os.path.basename(folder.rstrip("/"))

    # 1) charger l'index images -> (page, post_index, ...)
    index_mapping = load_image_index_for_folder(folder)

    per_image_path = os.path.join(interm_dir, f"{folder_name}_ocr_per_image.jsonl")
    per_scene_path = os.path.join(interm_dir, f"{folder_name}_ocr_scenes.jsonl")

    # dict clé = scene_id, valeur = dict avec meta + textes concaténés
    scenes: Dict[str, Dict[str, Any]] = {}

    with open(per_image_path, "w", encoding="utf-8") as f_img:
        for img_path in images:
            filename = os.path.basename(img_path)

            meta = index_mapping.get(filename)
            if meta is None:
                print(f"[WARN] Pas de meta pour {filename} dans l'index, on skip.")
                continue

            try:
                img = preprocess_image(img_path)
                text = ocr_image(img, lang="fra+eng")

                # 1) enregistrement par image
                rec_img: Dict[str, Any] = {
                    "topic_folder": folder_name,
                    "image_filename": filename,
                    "image_path": img_path,
                    "page": meta.get("page"),
                    "post_index": meta.get("post_index"),
                    "image_index": meta.get("image_index"),
                    "global_index": meta.get("global_index"),
                    "remote_url": meta.get("remote_url"),
                    "text": text,
                }
                f_img.write(json.dumps(rec_img, ensure_ascii=False) + "\n")
                print(f"OCR OK : {img_path}")

                # 2) regroupement par scène (page + post_index)
                page = meta.get("page")
                post_index = meta.get("post_index")
                scene_id = f"page_{page}_post_{post_index}"

                scene = scenes.get(scene_id)
                if scene is None:
                    scene = {
                        "scene_id": scene_id,
                        "topic_folder": folder_name,
                        "page": page,
                        "post_index": post_index,
                        "image_filenames": [],
                        "texts": [],
                    }
                    scenes[scene_id] = scene

                scene["image_filenames"].append(filename)
                scene["texts"].append(text)

            except Exception as e:
                print(f"Erreur OCR sur {img_path} : {e}")

    # 3) écrire un JSONL par scène
    with open(per_scene_path, "w", encoding="utf-8") as f_scene:
        for scene_id, scene in scenes.items():
            full_text = "\n".join(scene["texts"]).strip()
            rec_scene = {
                "scene_id": scene_id,
                "topic_folder": scene["topic_folder"],
                "page": scene["page"],
                "post_index": scene["post_index"],
                "image_filenames": scene["image_filenames"],
                "text": full_text,
            }
            f_scene.write(json.dumps(rec_scene, ensure_ascii=False) + "\n")

    print(f"\nOCR terminé.")
    print(f"- Résultat par image : {per_image_path}")
    print(f"- Résultat par scène : {per_scene_path}")


# -------------------------------------------------------
# Main
# -------------------------------------------------------

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
