import matplotlib.pyplot as plt
import squarify

# Data
labels = ['Rent', 'Kids', 'Food', 'Car', 'Clothes']
values = [1200, 900, 1000, 200, 100]

# Create the treemap
plt.figure(figsize=(8, 6))
squarify.plot(sizes=values, label=labels, alpha=0.8)
plt.axis('off')
plt.title("Monthly Expenses Treemap")
plt.show()
