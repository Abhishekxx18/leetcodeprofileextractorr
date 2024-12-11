import requests
from urllib.parse import urlencode
import csv
import json
import matplotlib.pyplot as plt
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

class APIError(Exception):
    """Exception raised for errors in the API response."""
    def __init__(self, message="An error occurred with the API"):
        self.message = message
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception raised for validation errors in input parameters."""
    def __init__(self, message="Invalid input parameter"):
        self.message = message
        super().__init__(self.message)


def build_url(base_url, endpoint, params=None):
    """Builds a complete URL with optional query parameters."""
    url = f"{base_url}{endpoint}"
    if params:
        query_string = urlencode(params)
        url = f"{url}?{query_string}"
    return url


def validate_username(username):
    """Validates the username input."""
    if not username or not isinstance(username, str):
        raise ValidationError("Username must be a non-empty string")


class LeetcodeWrapper:
    """A Python wrapper for the Alfa LeetCode API."""
    BASE_URL = "https://alfa-leetcode-api.onrender.com"

    def __init__(self, username):
        """Initializes the LeetcodeWrapper instance with the provided username."""
        validate_username(username)
        self.username = username

    def _request(self, endpoint, params=None):
        """Sends a GET request to the specified API endpoint."""
        url = build_url(self.BASE_URL, endpoint, params)
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.HTTPError as http_err:
            raise APIError(f"HTTP error occurred: {http_err}")
        except requests.exceptions.RequestException as req_err:
            raise APIError(f"Request error occurred: {req_err}")
        try:
            return response.json()
        except json.JSONDecodeError:
            raise APIError("Failed to parse JSON response")

    def get_profile(self):
        """Fetches the user's profile details."""
        return self._request(f"/{self.username}")

    def get_badges(self):
        """Fetches the badges earned by the user."""
        return self._request(f"/{self.username}/badges")

    def get_solved(self):
        """Fetches the total number of problems solved by the user."""
        return self._request(f"/{self.username}/solved")


def fetch_user_data(username):
    """Fetch user data using the Leetcode API wrapper."""
    api = LeetcodeWrapper(username)
    try:
        profile = api.get_profile()
        badges = api.get_badges()
        solved_problems = api.get_solved()

        user_data = {
            "Username": username,
            "Rating": profile.get("reputation", "N/A"),
            "Problems Solved": solved_problems.get("solvedProblem", "N/A"),
            "Badges": "N/A",
            "Ranking": profile.get("ranking", "N/A")
        }

        if badges and isinstance(badges.get("badges"), list):
            badge_names = [badge.get('displayName', 'N/A') for badge in badges.get("badges", [])]
            user_data["Badges"] = ", ".join(badge_names)

        return user_data
    except APIError as e:
        raise APIError(f"Failed to fetch data for {username}: {e}")


def rank_users(data):
    """Ranks users by rating and problems solved."""
    sorted_by_rating = sorted(data, key=lambda x: x.get("Rating", 0), reverse=True)
    sorted_by_solved = sorted(data, key=lambda x: x.get("Problems Solved", 0), reverse=True)
    return sorted_by_rating, sorted_by_solved


def visualize_data(data):
    """Creates a bar chart to visualize the distribution of ratings, problems solved, etc."""
    df = pd.DataFrame(data)
    # Convert columns to numeric, where possible, and drop any rows with 'N/A' or invalid values
    df["Rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    df["Problems Solved"] = pd.to_numeric(df["Problems Solved"], errors="coerce")
    df = df.dropna(subset=["Rating", "Problems Solved"])

    # Sort by Rating for visualization purposes
    df = df.sort_values(by="Rating", ascending=False)

    # Creating a plot with multiple metrics
    fig, ax = plt.subplots(figsize=(14, 8), facecolor='#f7f7f9')
    bar_width = 0.25
    index = range(len(df))

    # Plotting Rating, Problems Solved, and Ranking
    ax.bar(index, df["Rating"], bar_width, label="Rating", color='#76c7c0', edgecolor='#034752', linewidth=1.5)
    ax.bar([i + bar_width for i in index], df["Problems Solved"], bar_width, label="Problems Solved", color='#f7a800', edgecolor='#034752', linewidth=1.5)

    ax.set_xlabel("Users", fontsize=12, fontweight='bold')
    ax.set_ylabel("Scores", fontsize=12, fontweight='bold')
    ax.set_title("LeetCode User Performance", fontsize=16, fontweight='bold', color='#034752')
    ax.set_xticks([i + bar_width / 2 for i in index])
    ax.set_xticklabels(df["Username"], rotation=45, ha="right", fontsize=10, color='#333333')
    ax.legend()

    plt.tight_layout()
    plt.show()


def main():
    input_choice = input("Enter '1' to input usernames manually or '2' to upload a file: ").strip().lower()
    usernames = []

    if input_choice == "1":
        input_string = input("Enter comma-separated LeetCode usernames: ")
        usernames = [username.strip() for username in input_string.split(",")]
    elif input_choice == "2":
        file_path = input("Enter the file path: ").strip()
        try:
            with open(file_path, 'r') as file:
                usernames = [line.strip() for line in file.readlines() if line.strip()]
        except FileNotFoundError:
            print("File not found. Please check the file path and try again.")
            return
    else:
        print("Invalid choice. Exiting.")
        return

    print("\nFetching data for usernames...")
    results = []
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(fetch_user_data, username): username for username in usernames}
        for future in futures:
            try:
                results.append(future.result())
            except APIError as e:
                print(f"Error fetching data for {futures[future]}: {e}")
            except ValidationError as e:
                print(f"Validation error for {futures[future]}: {e}")

    print("\nRetrieved Data:")
    for user_data in results:
        print(f"Username: {user_data['Username']}")
        print(f"Rating: {user_data['Rating']}")
        print(f"Problems Solved: {user_data['Problems Solved']}")
        print(f"Badges: {user_data['Badges']}")
        print(f"Ranking: {user_data['Ranking']}\n")

    print("\nRanking users by performance...")
    ranked_by_rating, ranked_by_solved = rank_users(results)
    print("Top Users by Rating:")
    for user in ranked_by_rating[:5]:
        print(f"{user['Username']} - Rating: {user['Rating']}")
    print("\nTop Users by Problems Solved:")
    for user in ranked_by_solved[:5]:
        print(f"{user['Username']} - Problems Solved: {user['Problems Solved']}")

    visualize_choice = input("\nDo you want to visualize the data? (yes/no): ").strip().lower()
    if visualize_choice == "yes":
        visualize_data(results)

    save_choice = input("\nDo you want to save the data? (yes/no): ").strip().lower()
    if save_choice == "yes":
        file_name = input("Enter the file name (without extension): ").strip()
        file_format = input("Enter file format (csv/json): ").strip().lower()

        if file_format == "csv":
            with open(f'{file_name}.csv', 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=["Username", "Rating", "Problems Solved", "Badges", "Ranking"])
                writer.writeheader()
                writer.writerows(results)
            print(f"Data saved to '{file_name}.csv'.")
        elif file_format == "json":
            with open(f'{file_name}.json', 'w') as file:
                json.dump(results, file, indent=4)
            print(f"Data saved to '{file_name}.json'.")
        else:
            print("Invalid format. No file saved.")
    else:
        print("Data not saved.")


if __name__ == "__main__":
    main()
