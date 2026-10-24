import pandas as pd


df = pd.read_csv("C:\\HCL_USECASE\\data\\golden_it_support_tickets.csv")

json_data=df.to_json(orient="records",indent=4)

with open("C:\\HCL_USECASE\\data\\golden_it_support_tickets.json","w") as file:
    file.write(json_data)



