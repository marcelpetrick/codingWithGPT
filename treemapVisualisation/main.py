import matplotlib.pyplot as plt
import squarify
import matplotlib.cm as cm

# Data
labels = ['Rent', 'Kids', 'Food', 'Car', 'Clothes']
values = [1200, 900, 1000, 200, 100]
label_values = [f'{label}\n€{value}' for label, value in zip(labels, values)]

# Normalize values for colormap
min_val = min(values)
max_val = max(values)
normed = [(v - min_val) / (max_val - min_val) for v in values]

# Choose a colormap (red to green)
cmap = cm.get_cmap('RdYlGn_r')
colors = [cmap(n) for n in normed]

# Create the treemap
plt.figure(figsize=(8, 6))
squarify.plot(sizes=values, label=label_values, color=colors, alpha=0.8)
plt.axis('off')
plt.title("Monthly Expenses Treemap with Gradient Colors")
plt.tight_layout()
plt.savefig("monthly_expenses_treemap.png", dpi=300, bbox_inches='tight')
plt.show()
