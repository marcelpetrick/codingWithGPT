# Architecture

## C4 level 1 system context

This view shows who sets the light and what is outside the Linux controller.

```mermaid
C4Context
    title System context for the Cleware light controller
    Person(operator, "Operator", "Chooses the colors or pattern")
    System(controller, "Cleware light controller", "Runs on Linux")
    System_Ext(light, "Cleware USB-Ampel", "Runs the device firmware")
    Rel(operator, controller, "Runs color commands", "Terminal")
    Rel(controller, light, "Sends channel reports", "USB HID")
```

## C4 level 2 container view

This view shows how the Python process reaches the light.
The controller has one process and no data store.

```mermaid
C4Container
    title Containers for the Cleware light controller
    Person(operator, "Operator", "Chooses the colors or pattern")
    System_Boundary(host, "Cleware light controller") {
        Container(cli, "Traffic light CLI", "Python", "Builds one report per color")
    }
    System_Ext(kernel, "Linux hidraw", "Routes output reports to the matching USB device")
    System_Ext(light, "Cleware USB-Ampel", "Runs the device firmware")
    Rel(operator, cli, "Runs commands", "Terminal")
    Rel(cli, kernel, "Writes output reports", "Device file")
    Rel(kernel, light, "Sends channel reports", "USB HID")
```
