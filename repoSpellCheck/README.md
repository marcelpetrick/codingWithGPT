# What?

Tool to automate the spellchecking process for repositories.

Clone the repo, run codespell, check for results.


## Run

```bash
 python3 main.py repo=https://github.com/gemforce-team/wGemCombiner keep=1
```

## Check results

Here we see some typo in `dimensions`

```bash
git diff WGemCombiner/NativeMethods.cs | cat                                                                                                                                                    ✔ 
diff --git a/WGemCombiner/NativeMethods.cs b/WGemCombiner/NativeMethods.cs
index 015e622..8fde6a5 100644
--- a/WGemCombiner/NativeMethods.cs
+++ b/WGemCombiner/NativeMethods.cs
@@ -48,7 +48,7 @@
 
         [DllImport("user32.dll")]
         [return: MarshalAs(UnmanagedType.Bool)]
-        public static extern bool GetClientRect(IntPtr hWnd, out Rectangle lpRect); // grab the demensions of the window
+        public static extern bool GetClientRect(IntPtr hWnd, out Rectangle lpRect); // grab the dimensions of the window
 
         [return: MarshalAs(UnmanagedType.Bool)]
         [DllImport("user32.dll", SetLastError = true)]
    ~/repos/codingWithGPT/repoSpellCheck/codespell-run-y8tf6yck    master !4    
```

## Ideas for later
* confirm that are real typos - not just false positives (maybe exclude more weird files)
* if something is found, then report "yes, fix this"
* if found, then prepare the change request as commit? With proper commit message?
  * if this works, push to the proper repo and open an PR?!?

