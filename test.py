from prettytable import PrettyTable

x = PrettyTable()


x.header = False
x.add_row(["hithere"])
x.add_row(["potatois great"])

print(x)