**Prompt: GitLab Daily Activity Post-Processing**

You are given a GitLab activity export for a single user.
The activity is already grouped into daily buckets and includes timestamps, event types (e.g., commits, merge requests, comments, wiki updates, work items), and short descriptions.

Your task is to generate a **daily summary** with the following rules:

### For each day

1. **Summarize the work performed** in **no more than two sentences**.

   * Clearly state **what the person worked on** (e.g., feature development, bug fixing, CI/CD, documentation, project setup, code review, coordination).
   * **Group and generalize similar events** (e.g., multiple wiki edits → “updated documentation”; multiple commits → “iterated on implementation”).
   * Be as **specific as possible** while avoiding repetition of individual events.

2. **Estimate activity duration**:

   * Determine how long the person was active that day using the **timestamp of the first and last event**.
   * Report the result as an approximate number of **hours active**.

3. **Estimate effort level**:

   * Estimate effort based on the **type, breadth, and intensity of activities**, not on elapsed time.
   * Consider development work, CI setup, architectural changes, reviews, and coordination as higher effort than simple comments or minor edits.
   * Use qualitative levels such as *low*, *medium*, *high*, or *very high* effort, and integrate this naturally into the description.

4. **Days without activity**:

   * Explicitly state that there was **no recorded activity** and report **0 hours active**.

### Output format (must be exact)

```
day: <YYYY-MM-DD>: <daily activity summary>; ~<hours> hours active
-------
```

### Additional constraints

* Do not list individual events.
* Do not repeat the same wording across multiple days.
* Use clear, professional English suitable for engineering or management reporting.
* Assume all timestamps are in UTC.
* Do not include explanations, headings, or commentary outside the required format.
