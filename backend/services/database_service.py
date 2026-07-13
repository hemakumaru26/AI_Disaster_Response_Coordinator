import os
import pandas as pd

DATABASE = "database/incidents.csv"


def save_incident(data):

    if os.path.exists(DATABASE):

        df = pd.read_csv(DATABASE)

    else:

        df = pd.DataFrame(
            columns=[
                "reporter",
                "disaster",
                "location",
                "priority",
                "status"
            ]
        )

    df.loc[len(df)] = [
        data["reporter_name"],
        data["disaster_type"],
        data["location"],
        data["priority"],
        "Active"
    ]

    df.to_csv(DATABASE, index=False)