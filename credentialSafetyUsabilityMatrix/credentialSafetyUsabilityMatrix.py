# what best practices exist to keep credentials safe while using them in an ongoing project, which i version with git? i fear to commit the key accidentally while committing changes. they keys are part of a text-file, so humand readable. i heard about following techniques: setting them as environment-parameter, then using them in code. or maybe putting them into a file outside of the repo (which are then read during run time) would work? what other ways exist? list and rate all of them in terms of usability for the developer and the safety for the keys. make a chart.
#
# Great. For illustration purposes create me a python script which uses matplotlib or similar to create a 2d chart
# with lots of colors which maps all the technqiues versus usability (one axis) and safety(second axis).
#
# the labels overlap. this is not readable. make it human readable. maybe with some lines going to the data-point to the text label?

import matplotlib.pyplot as plt

# Data
techniques = [
    ("Environment variables", 4, 4),
    ("Separate file outside repo", 3, 4),
    ("Git ignore file", 5, 3),
    ("Encrypted secrets file", 2, 5),
    ("Secrets manager service", 2, 5),
]

# Extract data for plotting
labels, usability, safety = zip(*techniques)

# Create a colormap
cmap = plt.get_cmap("viridis")
colors = cmap([i / (len(techniques) - 1) for i in range(len(techniques))])

# Create the scatter plot
fig, ax = plt.subplots()
scatter = ax.scatter(usability, safety, c=colors)

# Set axis labels
ax.set_xlabel("Usability (1-5)")
ax.set_ylabel("Safety (1-5)")

# Add technique labels with lines
offsets = [(0.2, 0.3), (0.2, -0.3), (-0.4, 0.3), (-0.4, -0.3), (0.2, 0)]
for label, x, y, color, offset in zip(labels, usability, safety, colors, offsets):
    ax.text(x + offset[0], y + offset[1], label, fontsize=9, ha="left", va="bottom", color=color)
    ax.plot([x, x + offset[0]], [y, y + offset[1]], color=color, linestyle="--", linewidth=0.8)

# Set axis limits
ax.set_xlim(0, 6)
ax.set_ylim(0, 6)

# Add grid
ax.grid(True, linestyle="--", alpha=0.7)

# Show the plot
#plt.show() # close it before saving as file - else white canvas
plt.savefig("usability_vs_safety_matrix.png")

# ----------------------------------------------
#
# Best practices to keep credentials safe in a project versioned with Git can be ranked in terms of usability for the developer and safety for the keys. Here's a chart that lists and rates different techniques:
# Technique	Usability (1-5)	Safety (1-5)
# 1. Environment variables	4	4
# 2. Separate file outside repo (e.g., config file)	3	4
# 3. Git ignore file	5	3
# 4. Encrypted secrets file (e.g., Vault, KMS)	2	5
# 5. Using a secrets manager service (e.g., AWS Secrets Manager)	2	5
#
#     Environment variables: This method involves setting the credentials as environment variables on your local machine or the server. This is a popular and relatively easy way to store sensitive information. It keeps the keys out of the code and version control system.
#         Usability: 4
#         Safety: 4
#
#     Separate file outside repo: Place the credentials in a separate file (e.g., a JSON or YAML configuration file) that resides outside the Git repository. This keeps the keys out of the version control system while still being accessible by your code during runtime.
#         Usability: 3
#         Safety: 4
#
#     Git ignore file: Use a .gitignore file to ensure that any files containing sensitive information are not committed to the repository. This is easy to set up but carries the risk of accidentally committing the sensitive file if not configured properly.
#         Usability: 5
#         Safety: 3
#
#     Encrypted secrets file: Use a tool like HashiCorp Vault or a key management system (KMS) to store encrypted credentials. This is a secure way to manage secrets, but it can be more difficult to set up and use than other methods.
#         Usability: 2
#         Safety: 5
#
#     Using a secrets manager service: Use a managed secrets service like AWS Secrets Manager, Azure Key Vault, or Google Cloud Secret Manager to store and manage your credentials. This provides a high level of security, but it requires additional setup and may come with additional costs.
#         Usability: 2
#         Safety: 5
#
# It's important to choose a method that balances usability and safety based on the specific needs of your project. In general, using environment variables or a separate file outside the repository are good starting points for most projects.