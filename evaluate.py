import matplotlib.pyplot as plt

class fpl_evaluate:
    def __init__(self):
        pass
    
    def score_model(self, predictions, labels):
        # Calculate error
        error = 0
        square_error = 0
        accuracy = 0
        for i in range(len(predictions)):
            error += abs(predictions[i] - labels[i])
            square_error += (predictions[i] - labels[i]) ** 2
            if round(predictions[i]) == labels[i]:
                accuracy += 1
        error /= len(predictions)
        square_error /= len(predictions)
        accuracy /= len(predictions)

        return error, square_error, accuracy
    
    def display_weights(self, weights, feature_names, pos):
        # Plot the weights
        plt.title(f'GW{i} {pos} feature weights')
        plt.xlabel('Feature')
        plt.ylabel('Weight')
        plt.bar(feature_names, weights)
        plt.xticks(rotation=90)
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