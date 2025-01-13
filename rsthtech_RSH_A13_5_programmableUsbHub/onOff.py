import usb.core
import usb.util

# Find the hub device
dev = usb.core.find(idVendor=0x0bda, idProduct=0x5411)

if dev is None:
    raise ValueError("Device not found")

# Send control transfer to toggle power (vendor-specific command)
# Replace bRequest, wValue, wIndex with hub-specific values
dev.ctrl_transfer(0x23, 0x03, 0x0001, 0x0001, None)  # Example: Turn off
dev.ctrl_transfer(0x23, 0x03, 0x0001, 0x0000, None)  # Example: Turn on
