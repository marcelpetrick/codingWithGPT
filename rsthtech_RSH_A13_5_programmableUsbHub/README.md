# programmable usb hub (RSHTECH RSH-A13-5)

Control USB Hub Ports with Python and `uhubctl`.

## Installation (Manjaro Linux)

To install uhubctl using yay (an AUR helper):

```bash
yay -S uhubctl
```

## Usage

### Turn Off the First Port

To turn off the first port on a specific USB hub, run:

```bash
sudo uhubctl -l <hub-location> -p 1 -a 0
```

Replace <hub-location> with the location of the hub (e.g., 2-1).

### Turn On the First Port

To turn the first port back on:

```bash
sudo uhubctl -l <hub-location> -p 1 -a 1
```

### Example

If your hub location is 2-1, use:

```bash
sudo uhubctl -l 2-1 -p 1 -a 0  # Turn off
sudo uhubctl -l 2-1 -p 1 -a 1  # Turn on
```

This effectively toggles power to the first port of the hub.
