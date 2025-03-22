import unittest
import tempfile
import os
from PIL import Image
from convertToPng import (
    create_output_folder,
    get_image_files,
    convert_to_png,
    copy_png,
    process_images
)

class TestImageProcessor(unittest.TestCase):

    def setUp(self):
        # Temporary directory for input and output
        self.test_dir = tempfile.TemporaryDirectory()
        self.input_dir = self.test_dir.name
        self.output_dir = os.path.join(self.input_dir, 'png')

        # Create a sample JPEG image
        self.sample_jpg = os.path.join(self.input_dir, 'test.jpg')
        img = Image.new('RGB', (10, 10), color='red')
        img.save(self.sample_jpg, 'JPEG')

        # Create a sample PNG image
        self.sample_png = os.path.join(self.input_dir, 'test.png')
        img.save(self.sample_png, 'PNG')

    def tearDown(self):
        self.test_dir.cleanup()

    def test_create_output_folder(self):
        create_output_folder(self.output_dir)
        self.assertTrue(os.path.isdir(self.output_dir))

    def test_get_image_files(self):
        files = get_image_files(self.input_dir)
        self.assertIn('test.jpg', files)
        self.assertIn('test.png', files)

    def test_convert_to_png(self):
        dest_path = os.path.join(self.output_dir, 'converted.png')
        create_output_folder(self.output_dir)
        convert_to_png(self.sample_jpg, dest_path)
        self.assertTrue(os.path.isfile(dest_path))

    def test_copy_png(self):
        dest_path = os.path.join(self.output_dir, 'copied.png')
        create_output_folder(self.output_dir)
        copy_png(self.sample_png, dest_path)
        self.assertTrue(os.path.isfile(dest_path))

    def test_process_images(self):
        process_images(input_dir=self.input_dir, output_dir=self.output_dir)
        converted_file = os.path.join(self.output_dir, 'test.png')
        self.assertTrue(os.path.isfile(converted_file))

if __name__ == '__main__':
    unittest.main()
