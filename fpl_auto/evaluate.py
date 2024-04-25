import matplotlib.pyplot as plt
import numpy as np
import os
import math
import numpy as np
from scipy import stats
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
    plt.figure(figsize=(15, 6))
    # big title
    #plt.suptitle(f'GW{week_num} feature importances')
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
    # Plot predictions vs actual points
    # Plot predictions vs actual points for GWi
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
    # Create predictions/{season}/gw{week_num}/ directory
    directory = f'predictions/{season}/GW{week_num}/'
    os.makedirs(directory, exist_ok=True)

    positions = ['GK', 'DEF', 'MID', 'FWD']
    for i, position in enumerate(positions):
        clean_predictions[i].to_csv(f'{directory}{position}.tsv', sep='\t')

    print(f'- Saved to {directory}[POS].tsv')

def plot_p_minus_xp(p_list, xp_list, from_week, to_week):
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

def plot_score_comparison(p_list, global_avg, chips_usage, from_week, to_week, season):
    # Categorise each week as above or below average, where the average is 50 points
    week_count = range(from_week, from_week + len(p_list))
    # Categorise each week
    total_p = sum(p_list)
    avg_p = sum(p_list) / len(p_list)

    # Plot the data
    plt.title(f'{season} Performance - {round(total_p)} points total')
    plt.bar(week_count, p_list, label='Points Scored')
    
    #plt.axhline(fpl_avg, color='black', linestyle='--', label=f'FPL Avg {fpl_avg:.2f}')
    plt.axhline(avg_p, color='red', linestyle='--', label=f'Model Avg {avg_p:.2f}')
    if season == '2023-24':
        plt.axhline(global_avg, color='limegreen', linestyle='--', label=f'Global Avg {global_avg:.2f}')
    chip_colors = {'Triple Captain': 'mediumvioletred', 
                   'Bench Boost': 'orange', 
                   'Free Hit': 'blueviolet', 
                   'Wildcard': 'lightcoral'}
    for chip, i in chips_usage:
        plt.bar(i, p_list[i-from_week], color=chip_colors[chip], label=f'{chip} GW{i}', alpha=0.7)

    plt.xlabel('Gameweek')
    plt.ylabel('Points')
    plt.legend()

    # save the plot as png in results folder
    plt.savefig(f'results/{season}/{season}_{round(total_p)}_score_comparison.png')
    plt.show()

def plot_average_comparison(p_list, avg_list, from_week, to_week):
    # Categorise each week as above or below average, where the average is 50 points
    x_axis = np.arange(from_week, to_week + 1)[:len(p_list)]
    y_axis_one = p_list
    y_axis_two = avg_list[:len(p_list)]
    y_axis = y_axis_two - y_axis_one

    plt.bar(x_axis, y_axis)
    plt.xlabel('Gameweek')
    plt.ylabel('Points Difference')
    plt.show()

def plot_cumulative_points(p_list, season):
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
    Categorise each week as above or below average, where the average in avg_list"""
    bad = 0
    good = 0
    for i, p in enumerate(p_list):
        if p < avg_list[i]:
            bad += 1
        else:
            good += 1
    return good, bad

def box_plot_by_season(points, seasons):
    # Creating dataset    
    fig = plt.figure(figsize=(10, 7))

    y_axis = seasons
    box = plt.boxplot(points, patch_artist=True, vert=False)

    # Set the color of the boxes
    colors = ['lightblue', 'lightgreen', 'lightpink']
    for patch, color in zip(box['boxes'], colors):
        patch.set_facecolor(color)

    plt.xlabel('Points')
    plt.ylabel('Season')
    plt.title('Points Box Plot by Season')
    plt.yticks(range(1, len(y_axis) + 1), y_axis)
    plt.tight_layout()
    plt.show()

def box_plot_by_week(points, start_gw, end_gw, season):    
    fig = plt.figure(figsize=(10, 7))
    x_axis = np.arange(start_gw, end_gw)

    # Creating plot
    box = plt.boxplot(points, positions=x_axis, patch_artist=True)

    # Set the color of the boxes
    
    for patch in box['boxes']:
        patch.set_facecolor('lightblue')

    plt.xlabel('Gameweek')
    plt.ylabel('Points')
    plt.title(f'Box Plot of {season} Points')
    plt.show()

def point_distribution(points, season):
    sorted_points = np.sort(points)
    plt.hist(sorted_points, density=True)

    plt.xlabel('Team Points per Gameweek')
    plt.ylabel('Probability')

    # Generate random data
    data = sorted_points

    # Fit a normal distribution to the data
    mu, std = stats.norm.fit(data)

    # Plot the PDF.
    xmin, xmax = plt.xlim()
    x = np.linspace(xmin, xmax, 150)
    p = stats.norm.pdf(x, mu, std)
    plt.plot(x, p, 'k', linewidth=2)
    plt.title(f'Point Distribution for {season} Season, mu = {mu:.2f}, std = {std:.2f}')
    plt.show()

def export_results(season, points, xpoints, chip_usage, transfers):
    avg_p = round(sum(points) / len(points), 0)
    if len(points) < 38 and season != '2023-24':
        points.append(avg_p)

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

def plotxp(season, xp_list, start_gw, end_gw):
    x_axis = range(start_gw, end_gw)
    plt.bar(x_axis, xp_list[:len(x_axis)])
    plt.xticks(x_axis)
    plt.xlabel('Gameweek')
    plt.ylabel('Expected Points')
    plt.title(f'Expected Points over the {season} season | Total xP: {sum(xp_list):.2f}')
    
    # Plot the average line
    average = sum(xp_list) / len(xp_list)
    plt.axhline(average, color='red', linestyle='--', label='Average xP')
    
    plt.legend()
    plt.show()
