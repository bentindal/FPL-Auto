import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os
import math

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

def plot_score_comparison(p_list, from_week, to_week, season):
    # Categorise each week as above or below average, where the average is 50 points
    week_count = range(from_week, to_week + 1)
    # poor = 0-49, okay = 50-59, good = 60-69, excellent = 70+
    poor = np.zeros(len(week_count))
    okay = np.zeros(len(week_count))
    good = np.zeros(len(week_count))
    excellent = np.zeros(len(week_count))
    
    # Categorise each week
    for i, p in enumerate(p_list):
        if p < 50:
            poor[i] = p
        elif p < 60:
            okay[i] = p
        elif p < 70:
            good[i] = p
        else:
            excellent[i] = p
    avg_p = sum(p_list) / len(p_list)

    # Plot the data
    plt.title(f'Score Comparison - {season}')
    plt.bar(week_count, poor, label='Poor (< 50)', color='red')
    plt.bar(week_count, okay, label='Okay (>= 50)', color='orange', bottom=poor)
    plt.bar(week_count, good, label='Good (>= 60)', color='yellow', bottom=poor + okay)
    plt.bar(week_count, excellent, label='Excellent (>= 70)', color='green', bottom=poor + okay + good)
    plt.axhline(50, color='black', linestyle='-')
    plt.axhline(60, color='black', linestyle='-')
    plt.axhline(70, color='black', linestyle='-')
    plt.axhline(avg_p, color='purple', linestyle='--', label=f'Average = {avg_p:.2f}')
    plt.xlabel('Gameweek')
    plt.ylabel('Points')
    plt.legend()
    plt.show()

def plot_average_comparison(p_list, avg_list, from_week, to_week):
    # Categorise each week as above or below average, where the average is 50 points
    x_axis = np.arange(from_week, to_week + 1)[:len(p_list)]
    y_axis_one = p_list
    y_axis_two = avg_list[:len(p_list)]
    width = 0.35  # Width of each bar

    plt.bar(x_axis - width/2, y_axis_one, width=width, label='Actual P')
    plt.bar(x_axis + width/2, y_axis_two, width=width, label='Average P')
    plt.xlabel('Gameweek')
    plt.ylabel('Points')
    plt.legend()
    plt.show()

def score_model(p_list, avg_list):
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