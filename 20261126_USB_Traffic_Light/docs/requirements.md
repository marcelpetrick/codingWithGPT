# Work record and requirements

Linux detects the light. Cleware's source gives the control reports.
The live test requires write access to the HID device.

## Plan

1. Identify the light and record its USB interface. Allow 5 minutes.
2. Verify the command bytes against Cleware's source. Allow 10 minutes.
3. Write tests and implement the Python commands. Allow 15 minutes.
4. Run checks from a clean clone and review the commits. Allow 20 minutes.
5. Cycle the light and test a pair of colors when access is available. Allow 5 minutes.

## Requirements

| ID | Outcome | Decision and implementation | Acceptance check |
| --- | --- | --- | --- |
| USB-01 | Identify the hardware and describe what it can do. | Compare the USB descriptors with Cleware's Linux source and the controller data sheet. Record observed and inferred details in [README.md](../README.md). | Match the IDs and report sizes against the attached light. Check the controller claim against both sources. |
| USB-02 | Change the light from Python. | Use the Python standard library and Linux hidraw to avoid a third-party runtime dependency. Implement steady colors, a color cycle, all off, and documented flash intervals. | Check the reports for each operation with a fixture. Confirm changes with the attached light when the account can open its control port. |
| USB-03 | Keep tests, documentation and release checks in this directory. | Use Python unittest, Ruff, Black, coverage.py and pinned check tools. Use GitHub Actions for a standalone checkout of this directory. | Run the checks from a clean clone. Check the release archive, checksum, SBOM and changelog. Record the hosted workflow status. |

Choose one Linux source distribution for all supported CPU architectures.
The Python application uses only the standard library.
Use GNU GPL v3 or later for the source.
Use Python 3.14 for the verification and release pipeline.

## Chronological status

| Time (CET) | Step | Result |
| --- | --- | --- |
| 16:37 | Identify device | Linux sees `0d50:0008`, USB serial string `63813` and release field `0.80`. |
| 16:39 | Check the protocol | Cleware's source and the device descriptor agree on three output bytes. |
| 16:40 | Set the project boundary | Keep all changes below the project directory and commit on `master`. |

## Resume here

1. Run `lsusb -d 0d50:0008` to check for the light.
2. Run `getfacl /dev/input/by-id/usb-Cleware_GmbH_USB-Ampel_63813-hidraw` to check access.
3. Follow the setup and verification commands in [README.md](../README.md).
