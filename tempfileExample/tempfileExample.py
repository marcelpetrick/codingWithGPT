import tempfile
import os

# Create a temporary directory
with tempfile.TemporaryDirectory() as temp_dir:
    print("Temporary directory:", temp_dir)

    # Set the permissions for the temporary directory
    os.chmod(temp_dir, 0o700)  # Read, write, and execute permissions for the owner only

    # Create a temporary file inside the directory
    with tempfile.NamedTemporaryFile(dir=temp_dir, prefix="example_", suffix=".txt", delete=False) as temp_file:
        temp_file_path = temp_file.name
        print("Temporary file:", temp_file_path)

        # Write some content to the temporary file
        temp_file.write(b"Example content")

        # Ensure that the content is written to disk
        temp_file.flush()

        # Set the permissions for the temporary file
        os.chmod(temp_file_path, 0o600)  # Read and write permissions for the owner only

        # Prevent closing
        while True:
            a = 1

        # Do further operations with the temporary file...

    # The temporary file has been automatically deleted by NamedTemporaryFile

# The temporary directory has been automatically deleted by TemporaryDirectory
