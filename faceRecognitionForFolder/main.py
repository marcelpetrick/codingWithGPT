import face_recognition
from pathlib import Path
import shutil

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

    # Iterate through all images in folder
    for image_path in IMAGES_FOLDER.iterdir():
        if image_path.is_file() and image_path.suffix.lower() in {".jpg", ".jpeg", ".png"}:
            try:
                unknown_image = face_recognition.load_image_file(image_path)
                unknown_encodings = face_recognition.face_encodings(unknown_image)
                for unknown_encoding in unknown_encodings:
                    match = face_recognition.compare_faces(
                        [reference_encoding], unknown_encoding, tolerance=TOLERANCE
                    )[0]
                    if match:
                        print(f"Match found: {image_path.name}")
                        shutil.copy(image_path, OUTPUT_FOLDER / image_path.name)
                        break  # Don't need to check other faces in the same image
            except Exception as e:
                print(f"Could not process {image_path.name}: {e}")

if __name__ == "__main__":
    main()
