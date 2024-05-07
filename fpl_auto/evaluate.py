import matplotlib.pyplot as plt
import numpy as np
import os
import math
import numpy as np
import json
import os

def score_model(predictions, labels):
    """
    Calculate the error, mean squared error (RMSE), and accuracy of the model's predictions.

    Args:
        predictions (list): The predicted values.
        labels (list): The actual values.

    Returns:
        tuple: A tuple containing the error, RMSE, and accuracy.
    """
    # Calculate error
    error = 0
    mse = 0
    accuracy = 0
    for i in range(len(predictions)):
        error += abs(predictions[i] - labels[i])
        mse += (predictions[i] - labels[i]) ** 2
        if round(predictions[i]) == labels[i]:
            accuracy += 1
    error /= len(predictions)
    mse /= len(predictions)
    accuracy /= len(predictions)

    return error, math.sqrt(mse), accuracy

def display_weights(week_num, weights, feature_names, pos):
    """
    Display the feature importances for each position.

    Args:
        week_num (int): The gameweek number.
        weights (list): A list of lists containing the feature importances for each position.
        feature_names (list): A list of feature names.
        pos (list): A list of positions.
    """
    plt.figure(figsize=(15, 6))
    plt.suptitle(f'GW{week_num} feature importances')
    # 4 subplots
    for i in range(4):
        plt.subplot(1, 4, i + 1)
        plt.title(pos[i])
        plt.barh(feature_names, weights[i])
        plt.xlabel('Importance')
        # Hide y axis labels for all but first subplot
        if i != 0:
            plt.yticks([])
        if i == 0:
            plt.ylabel('Feature')
        plt.gca().invert_yaxis()

    plt.tight_layout()
    plt.show()

def plot_predictions(predictions, test_data, week_num):
    """
    Plots the predictions against the actual points for each position.

    Args:
        predictions (list): A list of predictions for each position.
        test_data (list): A list of tuples containing the test features and labels for each position.
        week_num (int): The gameweek number.
    """
    # Plot predictions vs actual points
    gk_predictions, def_predictions, mid_predictions, fwd_predictions = predictions

    # Colour code by position
    plt.title(f'GW{week_num} predictions vs actual points')
    plt.xlabel('Predicted points')
    plt.ylabel('Actual points')
    plt.scatter(gk_predictions, test_data[0][1], color='red')
    plt.scatter(def_predictions, test_data[1][1], color='blue')
    plt.scatter(mid_predictions, test_data[2][1], color='green')
    plt.scatter(fwd_predictions, test_data[3][1], color='orange')

    plt.legend(['GK', 'DEF', 'MID', 'FWD'])
    # Plot y=x line to show perfect prediction
    plt.plot([0, 20], [0, 20], color='black')
    plt.show()

def export_tsv(clean_predictions, season, week_num):
    """
    Export the predictions to a TSV file for each position.

    Args:
        clean_predictions (list): A list of DataFrames containing the predictions for each position.
        season (str): The season for which the predictions were made.
        week_num (int): The gameweek number.
    """
    # Create predictions/{season}/gw{week_num}/ directory
    directory = f'predictions/{season}/GW{week_num}/'
    os.makedirs(directory, exist_ok=True)

    positions = ['GK', 'DEF', 'MID', 'FWD']
    for i, position in enumerate(positions):
        # sort by xP
        clean_predictions[i] = clean_predictions[i].sort_values(by='xP', ascending=False)
        clean_predictions[i].to_csv(f'{directory}{position}.tsv', sep='\t')

    print(f'- Saved predictions to {directory}[POS].tsv')

def plot_p_minus_xp(p_list, xp_list, from_week, to_week):
    """
    Plots the difference between the actual points and expected points for each gameweek.
    
    Args:
        p_list (list): A list of points scored in each gameweek.
        xp_list (list): A list of expected points for each gameweek.
        from_week (int): The starting gameweek index.
        to_week (int): The ending gameweek index.
    
    """
    # X-axis is Gameweeks
    x_data = range(from_week, to_week + 1)[:len(p_list)]
    # Y-axis is P - xP
    differences = [p - xp for p, xp in zip(p_list, xp_list)]
    plt.title('Actual Points minus Expected Points')
    plt.bar(x_data, differences, label='P - xP')
    
    # Calculate the average
    if len(differences) == 0:
        average = 0
    else:
        average = sum(differences) / len(differences)
    
    # Plot the average line
    plt.axhline(average, color='red', linestyle='--', label='Average = {:.2f}'.format(average))
    
    plt.legend()
    plt.show()

def plot_score_comparison(p_list, chips_usage, from_week, season):
    """
    Plots a comparison of the points scored in each gameweek with the average points scored.

    Args:
        p_list (list): A list of points scored in each gameweek.
        chips_usage (list): A list of tuples containing the chip used and the corresponding gameweek index.
        from_week (int): The starting gameweek index.
        season (str): The season for which the performance is being evaluated.
    """
    # Categorise each week as above or below average, where the average is 50 points
    week_count = range(from_week, from_week + len(p_list))
    # Categorise each week
    avg_p = sum(p_list) / len(p_list)
    total_p = sum(p_list) + avg_p * (38 - len(p_list))

    # Plot the data
    plt.bar(week_count, p_list, label='Points Scored')
    
    #plt.axhline(fpl_avg, color='black', linestyle='--', label=f'FPL Avg {fpl_avg:.2f}')
    plt.axhline(avg_p, color='red', linestyle='--', label=f'Model Avg {avg_p:.2f}')
    
    chip_colors = {'Triple Captain': 'mediumvioletred', 
                   'Bench Boost': 'orange', 
                   'Free Hit': 'blueviolet', 
                   'Wildcard': 'lightcoral'}
    for chip, i in chips_usage:
        plt.bar(i, p_list[i-from_week], color=chip_colors[chip], label=f'{chip} GW{i}', alpha=0.7)

    # For the weeks that remain in the season, plot the global average
    if len(p_list) < 38:
        plt.title(f'{season} Projected Performance - {round(total_p)} points total')
        for i in range(len(p_list) + 1, 39):
            plt.bar(i, avg_p, color='grey', label=f'Averaged GW{i}', alpha=0.7)
    else:
        plt.title(f'{season} Performance - {round(total_p)} points total')
    plt.xlabel('Gameweek')
    plt.ylabel('Points')
    plt.legend()

    # save the plot as png in results folder
    plt.savefig(f'results/{season}/{season}_{round(total_p)}_score_comparison.png')
    plt.show()

def plot_average_comparison(p_list, avg_list, from_week, to_week):
    """
    Plots the difference between the actual points and the global average points for each gameweek.

    Args:
        p_list (list): A list of points scored in each gameweek.
        avg_list (list): A list of the global average points for each gameweek.
        from_week (int): The starting gameweek index.
        to_week (int): The ending gameweek index.
    """
    # Categorise each week as above or below average, where the average is 50 points
    x_axis = np.arange(from_week, to_week + 1)[:len(p_list)]
    y_axis_one = p_list
    y_axis_two = avg_list[:len(p_list)]
    y_axis =  y_axis_one - y_axis_two

    plt.bar(x_axis, y_axis)
    plt.xlabel('Gameweek')
    plt.ylabel('Points Difference')
    plt.title('Points Difference from Global Average')
    plt.show()

def plot_cumulative_points(p_list, season):
    """
    Plots the cumulative points scored over the course of the season.

    Args:
        p_list (list): A list of points scored in each gameweek.
        season (str): The season for which the performance is being evaluated.
    """
    # Calculate the cumulative points
    cumulative_points = np.cumsum(p_list)
    x_axis = np.arange(1, len(p_list) + 1)

    plt.plot(x_axis, cumulative_points)
    plt.xlabel('Gameweek')
    plt.ylabel('Cumulative Points')
    plt.title(f'Cumulative Points for {season}')
    plt.show()

def score_model_against_list(p_list, avg_list):
    """
    Compares the model's predictions against the global average.

    Args:
        p_list (list): A list of points scored in each gameweek.
        avg_list (list): A list of the global average points for each gameweek.

    Returns:
        tuple: A tuple containing the number of weeks where the model performed better than the global average and the number of weeks where the model performed worse.
    """
    bad = 0
    good = 0
    for i, p in enumerate(p_list):
        if p < avg_list[i]:
            bad += 1
        else:
            good += 1
    return good, bad

def box_plot_by_season(points, seasons):
    """
    Creates a box plot of the points scored in each season.

    Args:
        points (list): A list of lists containing the points scored in each gameweek for each season.
        seasons (list): A list of the seasons for which the points are being plotted.
    """
    # Creating dataset    
    fig = plt.figure(figsize=(10, 7))

    y_axis = seasons
    box = plt.boxplot(points, patch_artist=True, vert=False)

    # Set the color of the boxes
    colors = ['lightblue', 'lightgreen', 'lightpink', 'lightyellow']
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)

    plt.xlabel('Points')
    plt.ylabel('Season')
    plt.title('Points Box Plot by Season')
    plt.yticks(range(1, len(y_axis) + 1), y_axis)
    plt.tight_layout()

    plt.show()

def export_results(season, points, xpoints, chip_usage, transfers):
    """
    Export the results of the model to a JSON file.

    Args:
        season (str): The season for which the results are being exported.
        points (list): A list of points scored in each gameweek.
        xpoints (list): A list of expected points for each gameweek.
        chip_usage (list): A list of tuples containing the chip used and the corresponding gameweek index.
        transfers (list): A list of tuples containing the transfer made and the corresponding gameweek index.
    """
    # Combine the data into a dictionary
    data = {
        "season": season,
        "points": points,
        "xpoints": xpoints,
        "chip_usage": chip_usage,
        "transfers": transfers
    }

    # Export the data as a JSON file
    # Create the directory if it doesn't exist
    directory = f"results/{season}"
    os.makedirs(directory, exist_ok=True)

    # Write the JSON file
    with open(f"{directory}/{season}_{sum(points)}_results.json", "w+") as file:
        json.dump(data, file)

    print('Results saved!')

def plotxp(season, xp_list, start_gw, end_gw, chips_usage):
    """
    Plots the expected points for each gameweek.

    Args:
        season (str): The season for which the expected points are being plotted.
        xp_list (list): A list of expected points for each gameweek.
        start_gw (int): The starting gameweek index.
        end_gw (int): The ending gameweek index.
        chips_usage (list): A list of tuples containing the chip used and the corresponding gameweek index.
    """
    x_axis = range(start_gw, end_gw)
    plt.figure(figsize=(20, 5))
    plt.bar(x_axis, xp_list[:len(x_axis)])
    plt.xticks(x_axis)
    plt.xlabel('Gameweek')
    plt.ylabel('Expected Points')
    plt.title(f'Expected Points over the {season} season | Total xP: {sum(xp_list):.2f}')
    
    # Plot the average line
    average = sum(xp_list) / len(xp_list)
    plt.axhline(average, color='red', linestyle='--', label='Average xP')

    chip_colors = {'Triple Captain': 'mediumvioletred', 
                   'Bench Boost': 'orange', 
                   'Free Hit': 'blueviolet', 
                   'Wildcard': 'lightcoral'}
    for chip, i in chips_usage:
        plt.bar(i, xp_list[i-start_gw], color=chip_colors[chip], label=f'{chip} GW{i}', alpha=0.7)
    
    plt.legend()
    plt.show()
