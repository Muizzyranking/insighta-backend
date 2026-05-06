import csv
import random

GENDERS = ["male", "female"]
AGE_GROUPS = ["child", "teenager", "adult", "senior"]
COUNTRIES = ["NG", "US", "GB", "GH", "KE", "ZA", "BR", "IN", "FR", "DE"]


def age_group(age):
    if age <= 12:
        return "child"
    if age <= 19:
        return "teenager"
    if age <= 59:
        return "adult"
    return "senior"


with open("test_500k.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "name",
            "gender",
            "gender_probability",
            "age",
            "country_id",
            "country_probability",
        ]
    )
    for i in range(500_000):
        age = random.randint(1, 90)
        writer.writerow(
            [
                f"Test User {i}",
                random.choice(GENDERS),
                round(random.uniform(0.7, 1.0), 2),
                age,
                random.choice(COUNTRIES),
                round(random.uniform(0.5, 1.0), 2),
            ]
        )

print("Done")
