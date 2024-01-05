import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

class fpl_evaluate:
    def score_model(self, predictions, labels):
        # Calculate error
        error = 0
        square_mean_error = 0
        accuracy = 0
        for i in range(len(predictions)):
            error += abs(predictions[i] - labels[i])
            square_mean_error += (predictions[i] - labels[i]) ** 2
            if round(predictions[i]) == labels[i]:
                accuracy += 1
        error /= len(predictions)
        square_mean_error /= len(predictions)
        accuracy /= len(predictions)

        return error, square_mean_error, accuracy
    
    def display_weights(self, week_num, weights, feature_names, pos):
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

    def plot_predictions(self, predictions, test_data, week_num):
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

    def export_tsv(self, player_names, predictions, week_num):
        # Output predictions to tsv, use player_names as first column, then predictions
        tsv_gk_predictions = np.column_stack((player_names[0], predictions[0]))
        tsv_gk_predictions = np.concatenate((np.array([['Name', 'xP']]), tsv_gk_predictions), axis=0)
        tsv_gk_predictions = pd.DataFrame(tsv_gk_predictions[1:], columns=tsv_gk_predictions[0])
        tsv_gk_predictions.set_index('Name', inplace=True)
        tsv_gk_predictions.to_csv(f'predictions/gw{week_num}_GK.tsv', sep='\t')

        tsv_def_predictions = np.column_stack((player_names[1], predictions[1]))
        tsv_def_predictions = np.concatenate((np.array([['Name', 'xP']]), tsv_def_predictions), axis=0)
        tsv_def_predictions = pd.DataFrame(tsv_def_predictions[1:], columns=tsv_def_predictions[0])
        tsv_def_predictions.set_index('Name', inplace=True)
        tsv_def_predictions.to_csv(f'predictions/gw{week_num}_DEF.tsv', sep='\t')

        tsv_mid_predictions = np.column_stack((player_names[2], predictions[2]))
        tsv_mid_predictions = np.concatenate((np.array([['Name', 'xP']]), tsv_mid_predictions), axis=0)
        tsv_mid_predictions = pd.DataFrame(tsv_mid_predictions[1:], columns=tsv_mid_predictions[0])
        tsv_mid_predictions.set_index('Name', inplace=True)
        tsv_mid_predictions.to_csv(f'predictions/gw{week_num}_MID.tsv', sep='\t')

        tsv_fwd_predictions = np.column_stack((player_names[3], predictions[3]))
        tsv_fwd_predictions = np.concatenate((np.array([['Name', 'xP']]), tsv_fwd_predictions), axis=0)
        tsv_fwd_predictions = pd.DataFrame(tsv_fwd_predictions[1:], columns=tsv_fwd_predictions[0])
        tsv_fwd_predictions.set_index('Name', inplace=True)
        tsv_fwd_predictions.to_csv(f'predictions/gw{week_num}_FWD.tsv', sep='\t')

        print(f'- Saved to predictions/gw{week_num}_[POS].tsv')