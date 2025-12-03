import os
import re
import json
import random
import time
from typing import List

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from config import IMAGES_DIR, ensure_dirs, HEADERS


# -------------------------------------------------------
# HTTP utils
# -------------------------------------------------------

def protected_get(url: str, max_retries: int = 4) -> requests.Response:
    """
    GET robuste avec headers + retry sur 429.
    """
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)

            if resp.status_code == 200:
                return resp

            if resp.status_code == 429:
                wait = 2 ** attempt + random.random()
                print(f"[429] Trop de requêtes sur {url}. Attente {wait:.1f}s...")
                time.sleep(wait)
                continue

            resp.raise_for_status()

        except requests.exceptions.RequestException as e:
            print(f"[ERREUR] {e} sur {url}")
            time.sleep(2)

    raise RuntimeError(f"Échec GET {url} après {max_retries} tentatives")


def fetch_html(url: str) -> str:
    """
    Récupère le HTML et détecte la redirection vers une autre page
    (utile quand on dépasse la dernière page du topic).
    """
    resp = protected_get(url)
    if resp.url.rstrip("/") != url.rstrip("/"):
        raise ValueError(f"Redirection détectée : {url} -> {resp.url}")
    return resp.text


# -------------------------------------------------------
# Parsing HTML
# -------------------------------------------------------

def extract_image_urls_from_post(post, base_url: str) -> List[str]:
    """
    Retourne toutes les URLs d'images .png pour UN post (balise <article>).
    On réutilise ta logique alt / parent <a> / data-src / src.
    """
    urls: List[str] = []

    for img in post.find_all("img"):
        alt = img.get("alt")
        if not alt or not alt.lower().endswith(".png"):
            continue

        final_url = None

        # 1) parent <a href="...png">
        parent = img.parent
        if parent and parent.name == "a":
            href = parent.get("href")
            if href and href.lower().endswith(".png"):
                if href.startswith("http://") or href.startswith("https://"):
                    final_url = href
                else:
                    final_url = urljoin(base_url, href)

        # 2) data-src
        if final_url is None:
            data_src = img.get("data-src")
            if data_src and data_src.lower().endswith(".png"):
                if data_src.startswith("http://") or data_src.startswith("https://"):
                    final_url = data_src
                else:
                    final_url = urljoin(base_url, data_src)

        # 3) src
        if final_url is None:
            src = img.get("src")
            if src and src.lower().endswith(".png"):
                if src.startswith("http://") or src.startswith("https://"):
                    final_url = src
                else:
                    final_url = urljoin(base_url, src)

        if final_url:
            urls.append(final_url)

    return urls


def download_image_bytes(url: str) -> bytes:
    resp = protected_get(url)
    return resp.content


def normalize_topic_url(url: str) -> str:
    """
    Retire la partie /page/N/ si l'URL pointait vers une page spécifique.
    """
    url = url.strip()
    parts = url.split("/page/")
    base = parts[0]
    return base.rstrip("/")


def generate_folder_name(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    return text or "default"


def get_faction_name(base_url: str) -> str:
    resp = protected_get(base_url)
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    h1 = soup.find("h1", class_="ipsType_pageTitle ipsContained_container")
    if not h1:
        raise RuntimeError("Impossible de trouver le h1")

    title_text = h1.get_text(strip=True)
    if not title_text:
        raise RuntimeError("h1 vide")

    return title_text


# -------------------------------------------------------
# Scraping multi-pages + index par post
# -------------------------------------------------------

def scrape_all_pages(
    base_url: str,
    dest_dir: str,
    start_page: int = 1,
    max_pages: int = 200
) -> None:
    """
    - Parcourt les pages du topic.
    - Pour chaque page :
        - pour chaque post (<article.cPost>), récupère les images .png
        - télécharge les images avec un compteur global
        - écrit un index JSONL pour lier :
            page / post_index / image_index -> fichier local + URL distante
    """
    ensure_dirs()
    os.makedirs(dest_dir, exist_ok=True)

    # index JSONL pour relier images -> scène (post)
    base_dir = os.path.abspath(os.path.join(dest_dir, "..", ".."))
    interm_dir = os.path.join(base_dir, "interm")
    os.makedirs(interm_dir, exist_ok=True)

    topic_folder = os.path.basename(dest_dir.rstrip("/"))
    index_path = os.path.join(interm_dir, f"{topic_folder}_images_index.jsonl")

    file_counter = 1

    with open(index_path, "w", encoding="utf-8") as index_file:
        for page in range(start_page, max_pages + 1):
            url = f"{base_url}/page/{page}/"
            print(f"\n=== PAGE {page} ===")

            try:
                html = fetch_html(url)
            except ValueError as redirection_err:
                print(f"Fin : redirection détectée (dernière page atteinte ?) -> {redirection_err}")
                break
            except Exception as e:
                print(f"Fin : impossible de charger la page {page} ({e})")
                break

            soup = BeautifulSoup(html, "html.parser")
            posts = soup.find_all("article", class_="cPost")

            if not posts:
                print("Aucun post trouvé sur cette page.")
                continue

            images_found_on_page = 0

            for post_idx, post in enumerate(posts, start=1):
                img_urls = extract_image_urls_from_post(post, base_url=url)

                if not img_urls:
                    continue

                for img_idx, img_url in enumerate(img_urls, start=1):
                    try:
                        ext = os.path.splitext(img_url)[1].lower() or ".png"
                        filename = f"{file_counter:05d}{ext}"
                        full_path = os.path.join(dest_dir, filename)

                        content = download_image_bytes(img_url)
                        with open(full_path, "wb") as f:
                            f.write(content)

                        record = {
                            "topic_folder": topic_folder,
                            "page": page,
                            "post_index": post_idx,
                            "image_index": img_idx,
                            "global_index": file_counter,
                            "local_path": full_path,
                            "filename": filename,
                            "remote_url": img_url,
                        }
                        index_file.write(json.dumps(record, ensure_ascii=False) + "\n")

                        print(f"Téléchargé {file_counter:05d} : [page {page} post {post_idx} img {img_idx}] {img_url} -> {full_path}")

                        file_counter += 1
                        images_found_on_page += 1

                        time.sleep(random.uniform(1.0, 3.0))
                    except Exception as e:
                        print(f"Erreur téléchargement {img_url} : {e}")

            if images_found_on_page == 0:
                print("Aucune image trouvée sur cette page.")
            else:
                print(f"{images_found_on_page} images téléchargées sur la page {page}.")

    print(f"\nScraping terminé. Index images écrit dans : {index_path}")


# -------------------------------------------------------
# Main
# -------------------------------------------------------

if __name__ == "__main__":
    forum_url = input("Lien du topic : ").strip()
    base_url = normalize_topic_url(forum_url)

    try:
        faction_name = get_faction_name(base_url)
        print("Nom faction : ", faction_name)
        folder_name = generate_folder_name(faction_name)
    except Exception as e:
        print("Erreur, impossible de récupérer le nom de la faction :", e)
        folder_name = "default"

    dest_dir = os.path.join(IMAGES_DIR, folder_name)

    scrape_all_pages(base_url=base_url, dest_dir=dest_dir, start_page=1)
