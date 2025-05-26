import face_recognition
from pathlib import Path
import shutil
from tqdm import tqdm
import multiprocessing as mp

REFERENCE_IMAGE_PATH = Path("/home/mpetrick/Desktop/private/me_cropped.jpg")
IMAGES_FOLDER = Path("/home/mpetrick/Downloads/20250526_HTech_Ortus_pictures/HTECHxHPE_EMEA1/")
OUTPUT_FOLDER = Path("/home/mpetrick/Downloads/20250526_HTech_Ortus_pictures/HTECHxHPE_EMEA1/meFiltered")
TOLERANCE = 0.5  # Adjust for stricter or looser matching
CORES = 12  # Number of parallel processes

def process_image(args):
    image_path, reference_encoding, tolerance = args
    try:
        unknown_image = face_recognition.load_image_file(image_path)
        unknown_encodings = face_recognition.face_encodings(unknown_image)
        for unknown_encoding in unknown_encodings:
            match = face_recognition.compare_faces([reference_encoding], unknown_encoding, tolerance=tolerance)[0]
            if match:
                return (image_path, True, None)
        return (image_path, False, None)
    except Exception as e:
        return (image_path, False, str(e))

def main():
    OUTPUT_FOLDER.mkdir(exist_ok=True)

    # Load reference face encoding
    reference_image = face_recognition.load_image_file(REFERENCE_IMAGE_PATH)
    reference_encodings = face_recognition.face_encodings(reference_image)
    if not reference_encodings:
        print(f"No face found in reference image: {REFERENCE_IMAGE_PATH}")
        return
    reference_encoding = reference_encodings[0]

    image_files = [
        img for img in IMAGES_FOLDER.iterdir()
        if img.is_file() and img.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]
    total_images = len(image_files)
    print(f"Processing {total_images} images using {CORES} cores...")

    matches = 0
    errors = 0

    # Prepare arguments for each image
    args = [(img, reference_encoding, TOLERANCE) for img in image_files]

    # Use multiprocessing pool
    with mp.Pool(CORES) as pool:
        results = []
        for result in tqdm(pool.imap_unordered(process_image, args), total=total_images, desc="Scanning images", unit="img"):
            results.append(result)
            image_path, match, error = result
            if error:
                print(f"⚠️ Error ({image_path.name}): {error}")
                errors += 1
            elif match:
                print(f"✔️ Match: {image_path.name}")
                shutil.copy(image_path, OUTPUT_FOLDER / image_path.name)
                matches += 1
            else:
                print(f"✖️ No match: {image_path.name}")

    print(f"\nDone! Processed {total_images} images.")
    print(f"Matches found: {matches}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    main()
