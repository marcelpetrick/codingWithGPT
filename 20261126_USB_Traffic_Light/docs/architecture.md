# Architecture

## C4 level 1 system context

This view shows who sets the light and what is outside the Linux controller.

```mermaid
C4Context
    title System context for the Cleware light controller
    Person(operator, "Operator", "Chooses the colors or pattern")
    System(controller, "Cleware light controller", "Runs on Linux")
    System_Ext(light, "Cleware USB-Ampel", "Runs the device firmware")
    System_Ext(agents, "Local Claude and Codex clients", "Expose agent status and account limits")
    Rel(operator, controller, "Runs the controller or monitor", "Terminal")
    Rel(controller, agents, "Reads session status", "CLI JSON and local socket")
    Rel(controller, light, "Sends channel reports", "USB HID")
```

## C4 level 2 container view

This view shows how the manual controller and the status monitor reach the light.
They share Python code and keep no project data store.

```mermaid
C4Container
    title Containers for the Cleware light controller
    Person(operator, "Operator", "Chooses the colors or pattern")
    System_Boundary(host, "Cleware light controller") {
        Container(cli, "Traffic light CLI", "Python", "Builds one report per color")
        Container(monitor, "Agent status monitor", "Python", "Combines the four profile states")
    }
    System_Ext(kernel, "Linux hidraw", "Routes output reports to the matching USB device")
    System_Ext(light, "Cleware USB-Ampel", "Runs the device firmware")
    System_Ext(claude, "Claude profiles", "Provide active session state and local quota data")
    System_Ext(codex, "Codex App Server profiles", "Provide loaded thread status and account limits")
    Rel(operator, cli, "Runs commands", "Terminal")
    Rel(operator, monitor, "Starts monitoring", "Terminal")
    Rel(monitor, claude, "Reads agent state and cached limits", "CLI JSON and file")
    Rel(monitor, codex, "Reads thread, goal and quota state", "Unix socket")
    Rel(monitor, kernel, "Writes the combined color with the shared controller", "Device file")
    Rel(cli, kernel, "Writes output reports", "Device file")
    Rel(kernel, light, "Sends channel reports", "USB HID")
```
