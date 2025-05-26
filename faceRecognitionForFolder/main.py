import face_recognition
from pathlib import Path
import shutil
from tqdm import tqdm

REFERENCE_IMAGE_PATH = Path("/home/mpetrick/Desktop/private/me_cropped.jpg")
IMAGES_FOLDER = Path("/home/mpetrick/Downloads/20250526_HTech_Ortus_pictures/HTECHxHPE_EMEA1/")
OUTPUT_FOLDER = Path("/home/mpetrick/Downloads/20250526_HTech_Ortus_pictures/HTECHxHPE_EMEA1/meFiltered")
TOLERANCE = 0.5  # Adjust for stricter or looser matching

def main():
    OUTPUT_FOLDER.mkdir(exist_ok=True)

    # Load reference face encoding
    reference_image = face_recognition.load_image_file(REFERENCE_IMAGE_PATH)
    reference_encodings = face_recognition.face_encodings(reference_image)
    if not reference_encodings:
        print(f"No face found in reference image: {REFERENCE_IMAGE_PATH}")
        return
    reference_encoding = reference_encodings[0]

    # Gather images to process
    image_files = [
        img for img in IMAGES_FOLDER.iterdir()
        if img.is_file() and img.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]

    total_images = len(image_files)
    matches = 0
    errors = 0

    print(f"Processing {total_images} images...")

    for image_path in tqdm(image_files, desc="Scanning images", unit="img"):
        try:
            unknown_image = face_recognition.load_image_file(image_path)
            unknown_encodings = face_recognition.face_encodings(unknown_image)
            found = False
            for unknown_encoding in unknown_encodings:
                match = face_recognition.compare_faces(
                    [reference_encoding], unknown_encoding, tolerance=TOLERANCE
                )[0]
                if match:
                    print(f"✔️ Match: {image_path.name}")
                    shutil.copy(image_path, OUTPUT_FOLDER / image_path.name)
                    matches += 1
                    found = True
                    break  # Only need one matching face per image
            if not found:
                print(f"✖️ No match: {image_path.name}")
        except Exception as e:
            print(f"⚠️ Error ({image_path.name}): {e}")
            errors += 1

    print(f"\nDone! Processed {total_images} images.")
    print(f"Matches found: {matches}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    main()
