# Screen recording

On clients, Super+G opens the region selector. Drag an area, then wait for the
three-second centered on-screen countdown. Recording captures that region and system
output audio. Super+G again stops recording and finalizes the MP4 in the XDG
Videos directory (`~/media/video` on fi). Press Escape in the selector, or Super+G
during selection/countdown, to cancel. The microphone is not recorded. The countdown takes no keyboard focus and
disappears before capture starts; notifications are only used for saved files or errors.

Chezetc installs GPU Screen Recorder and Slurp from configured RPM repositories.
Tjikup updates those packages. The on-demand `screen-record.service` owns the
process, ensuring the shortcut stops only its recording. Recording also stops
when the graphical session ends. Failures produce a notification; inspect
`journalctl --user -u screen-record.service` for details.
