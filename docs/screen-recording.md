# Screen recording

On clients, Super+G opens the region selector. Drag an area, then wait for the
three-second centered on-screen countdown. Recording captures that region and system
output audio. Super+G again stops recording and finalizes the MP4 in the XDG
Videos directory (`~/media/video` on fi). Press Escape in the selector, or Super+G
during selection/countdown, to cancel. The microphone is not recorded. The countdown takes no keyboard focus and
fades out fully, followed by a half-second settling delay before capture starts; notifications are only used for saved files or errors.

Super+Ctrl+G opens the Hyprland sharing picker. Choose its window tab and select
the window to capture. This uses PipeWire window capture, so moving the window
does not leave recording pointed at its old screen area. Recording starts when
you confirm sharing, without the region countdown. Session restoration is disabled
so each new recording opens the picker.

Super+Shift+G opens a monitor picker: click an output to record its screen area
after the same three-second countdown. Keep the monitor layout unchanged while
recording. Super+G stops any mode; all three shortcuts stop an existing recording
or cancel a pending selection instead of starting another recorder.

Chezetc installs GPU Screen Recorder and Slurp from configured RPM repositories.
Tjikup updates those packages. The on-demand `screen-record.service` owns the
process, ensuring the shortcut stops only its recording. Recording also stops
when the graphical session ends. Failures produce a notification; inspect
`journalctl --user -u screen-record.service` for details.
