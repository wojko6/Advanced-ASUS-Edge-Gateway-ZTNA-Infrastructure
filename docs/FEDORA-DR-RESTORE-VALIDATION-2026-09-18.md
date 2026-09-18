# Fedora Disaster Recovery — clean-room restore validation

**Validation date:** 2026-09-18  
**Environment:** VMware Workstation test VM  
**Purpose:** Validate that the Fedora recovery set can be restored to a clean VM and boot into the recovered installed system.

## Result

**PASS — clean-room restore reached the recovered Fedora graphical desktop.**

The restored system booted from the recovered virtual NVMe disk after the recovery media was detached. The Live ISO was used only for the restore/chroot procedure and was then disconnected before the successful boot test.

## Validated

- / mounted from the recovered Btrfs root subvolume.
- /home mounted from the recovered Btrfs home subvolume.
- /boot mounted from the recovered ext4 boot partition.
- /boot/efi mounted from the recovered EFI system partition.
- The recovered user environment and project files were present after boot.
- systemctl --failed showed only mcelog.service.
- mcelog.service failure was identified as VM/CPU-specific: the daemon reports that AMD processor family 25 is unsupported and recommends the edac_mce_amd module.
- Initial /boot SELinux labels were incorrect (unlabeled_t) after restore.
- matchpathcon /boot established the expected policy label as system_u:object_r:boot_t:s0.
- restorecon -RFv /boot relabeled the restored boot tree according to Fedora SELinux policy.
- After relabeling, a new boot-level error scan produced no matches for boot, logind, selinux, denied, or mcelog.
- The restored system remained usable after returning to the VM and rerunning the validation checks.

## Recovery procedure findings

The clean-room test identified three restore requirements that should remain explicit in the recovery automation/documentation:

1. Regenerate or correct the /boot filesystem UUID references in /etc/fstab when the restored target uses a different partition identity.
2. Correct the corresponding /boot UUID reference in the Fedora EFI/GRUB configuration when required by the target layout.
3. Run a SELinux relabel of /boot after restoring its contents, using restorecon rather than a manually assigned chcon label.

These are recovery-target adaptation steps, not evidence that the source backup was corrupt.

## Known VM-specific exception

mcelog.service is not treated as a Disaster Recovery failure for this VMware validation. The service failed because the virtualized CPU exposed to the guest is not supported by mcelog; this is independent of filesystem recovery and boot integrity.

## Evidence boundary

This report intentionally omits deployment-specific identifiers such as exact filesystem UUIDs, host identifiers, network addresses, and other infrastructure-specific values. The raw recovery evidence remains local/private.

## Final assessment

The recovery set passed the most important practical test: a clean-room restore was booted successfully into the recovered Fedora installation, and the post-restore /boot SELinux labeling issue was identified, corrected, and revalidated.

**DR validation status: PASS.**