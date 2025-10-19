import csv

N = 11000

output_path = "data_large.csv"

fields = ["ID", "D1", "D2", "D3", "Fact1", "Fact2", "Fact3"]

D1_values = ["x1", "x2", "x3", "x4", "x5"]
D2_values = ["y1", "y2", "y3", "y4", "y5"]
D3_values = ["z1", "z2", "z3", "z4", "z5"]

with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(fields)

    for i in range(N):
        d1 = D1_values[i % 5]
        d2 = D2_values[(i * 2 + 1) % 5]
        d3 = D3_values[(i * 3 + 2) % 5]

        fact1 = (i % 200) + 1
        fact2 = (i % 100) * 10 + 10
        fact3 = (i % 1000) + 100

        writer.writerow([i, d1, d2, d3, fact1, fact2, fact3])

