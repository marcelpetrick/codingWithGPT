# CPU From Scratch issue review

Verdict: The three reported failure cases appear fixed. PR 4 introduces a negative-address regression. PR 6 leaves an older malformed-file behavior unchanged. Real Verilator validation remains open.

## Plan

1. Read issues 1–3 and pull requests 4–6. Allow 10 minutes. Done.
2. Inspect each change and run focused checks. Allow 30 minutes. Done.
3. Record findings and test limits. Allow 10 minutes. Done.

## Status

| Time (CET) | Status |
| --- | --- |
| 2026-11-02 11:24 | Started review of issues 1–3 and their proposed fixes. |
| 2026-11-02 11:25 | Inspected all three pull request diffs and runner code. |
| 2026-11-02 11:27 | Ran focused checks and recorded two boundary findings. |
| 2026-11-02 | Posted review comments on PRs 4–6 and linked them from issues 1–3. |

## Results

- Issue 1, PR 5, `7b53f32c5d04e6f889d2d5cdd7db1419bf588384`: A successful preprocessing run assembled. A missing include returned status 1. The previous binary remained on disk. The `just run` recipe stops when assembly fails. The check ran the recipe body in `sh` because `just` is unavailable.
- Issue 2, PR 4, `608d664163e181a55e39996511b0330eb2de6c50`: `.org 0x10` produced 16 zero words followed by the expected word. A mixed address 0 and 0x10 image also matched. The existing parser accepts negative `.org` values. The new packer silently drops negative-address words. For example, `.org -1` followed by `.word 0x12345678` succeeds with an empty image. Reject negative addresses before packing.
- Issue 3, PR 6, `b2af108b8933d3193d3272922f9b601d29bfd803`: A 4,097-word image exited with an error before the BRAM copy. Images of 4,095 and 4,096 words reached the socket setup. The actual changed C++ harness was compiled with simulated Verilator headers and a 4,096-word array. A real Verilator build was not available. `LoadProgram` drops incomplete trailing words. Therefore a 16,385-byte file is accepted as 4,096 words. Reject unaligned files and validate file size in bytes to enforce the stated image size rule.
- None of the pull requests has reported GitHub checks. No regression tests were added in their diffs.

## Reassessment of review findings

- PR 4: Valid regression, but negative addresses were already invalid for the target. The old assembler accepted `.org -1` and emitted its word at the start of the image. The PR instead silently drops it. Both behaviors are wrong. The PR changes silent misplacement to silent loss. Rejecting the address is a reasonable fix. Do not describe this as a normal-address failure.
- PR 5: The stale binary observation is true but is not a regression from this PR. It does not defeat the fix. Removing existing outputs is a separate design choice, not a requirement for this issue. The shell-body check does not prove an end-to-end `just` invocation.
- PR 6: Partial-word truncation is real but existed before this PR. A 16,385-byte file has 4,096 complete words, and the copy stays within BRAM. The original memory-safety issue is fixed for this case too. Rejecting malformed files is optional follow-up hardening, not a blocker for that fix. My original comment should have made that distinction clear. The stubbed harness test did not validate real Verilator compilation.
- The PRs add no regression tests. That is a test coverage gap, not proof that the changes fail.

## Posted comments

- [PR 4](https://github.com/BoergeSt/CPU-From-Scratch/pull/4#issuecomment-6574805961) and [issue 2](https://github.com/BoergeSt/CPU-From-Scratch/issues/2#issuecomment-6574808896).
- [PR 5](https://github.com/BoergeSt/CPU-From-Scratch/pull/5#issuecomment-6574805799) and [issue 1](https://github.com/BoergeSt/CPU-From-Scratch/issues/1#issuecomment-6574808653).
- [PR 6](https://github.com/BoergeSt/CPU-From-Scratch/pull/6#issuecomment-6574805802) and [issue 3](https://github.com/BoergeSt/CPU-From-Scratch/issues/3#issuecomment-6574808656).

## Resume here

State: Review and critical reassessment complete. The earlier GitHub comments have not been amended. Recheck the pull request heads before relying on this report.

Check commands: `gh pr view 4 --repo BoergeSt/CPU-From-Scratch --json headRefOid,state`; repeat for 5 and 6.

Restart commands: `git clone https://github.com/BoergeSt/CPU-From-Scratch.git /tmp/cpu-from-scratch-review-20261102`; `git -C /tmp/cpu-from-scratch-review-20261102 fetch origin '+refs/pull/*/head:refs/remotes/origin/review-pr*'`.
