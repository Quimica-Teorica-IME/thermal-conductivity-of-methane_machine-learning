# -*- coding: utf-8 -*-
"""SVR.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1aG9TyMZynkq-cQPBAZW2Eovl5WCK6BIj
"""

'''
This code uses Gradient Boosting model.
Gradient Boosting is a machine learning technique used for both regression and
classification tasks. It builds a predictive model in the form of an ensemble
of weak learners, typically decision trees, by sequentially adding them and
focusing on the mistakes made by the previous models. Each new model in the[
ensemble is trained to correct the errors of the previous ones.
'''

import os
import math
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import cross_val_score, cross_val_predict, train_test_split, GridSearchCV
from sklearn.metrics import (
    mean_squared_error,
    mean_absolute_error,
    accuracy_score,
    classification_report,
    r2_score,
    mean_absolute_percentage_error
)
from sklearn.ensemble import IsolationForest

from sklearn.svm import SVR
from sklearn.model_selection import LeaveOneOut

# ********************** FUNCTION DEFINITIONS **********************

def check_and_get_filename(directory, base_name, extension):
    """
    Check if the specific file already exists and create a new name if necessary.
    """
    count = 0
    while True:
        file_name = f"{base_name}{'' if count == 0 else f'_{count}'}.{extension}"
        full_path = os.path.join(directory, file_name)
        if not os.path.exists(full_path):
            return full_path
        count += 1

def save_to_file_and_print(message, file):
    """Prints a message and appends it to a file."""
    try:
        print(message)
        with open(file, 'a') as f:
            f.write(message)
    except Exception as e:
        print(f"An error occurred while saving the message to the file: {e}")


def format_value(value, decimal_places):
    format_string = "{:." + str(decimal_places) + "f}"
    return float(format_string.format(value))


def calculate_metrics(phase_name, y_true, y_pred, metrics_to_print=None, file=None):
    '''
    Calculates metrics.
    If no specific metrics are requested (metrics_to_print=None), it calculates
    and includes all available metrics in the message. Otherwise, it only
    calculates the necessary ones.
    The message is saved in a file if requested (file = 'name')
    '''
    if metrics_to_print is None:
        metrics_to_print = ['MAPE', 'MAE', 'MSE', 'RMSE', 'R2']

    metric_functions = {
        'MAPE': lambda y_true, y_pred: mean_absolute_percentage_error(y_true, y_pred),
        'MAE': mean_absolute_error,
        'MSE': mean_squared_error,
        'RMSE': lambda y_true, y_pred: math.sqrt(mean_squared_error(y_true, y_pred)),
        'R2': r2_score
    }

    output_message = f'\nMetrics for {phase_name} phase:\n'

    for metric in metrics_to_print:
        value = metric_functions[metric.upper()](y_true, y_pred)
        if metric.upper() == 'MAPE':
            formatted_value = format_value(value, 2)
            formatted_value = f'{formatted_value*100}%'
        else:
            formatted_value = format_value(value, 6)
        output_message += f"{metric}: {formatted_value}\n"

    if file:
        save_to_file_and_print(output_message, file)

    return output_message




def plot_overfitting_evaluation(y_train, y_test, save_path=None, name=None, phase_name=None):
    plt.figure(figsize=(8, 6))
    plt.scatter(y_train, y_test, color='red', label='Test', marker = 'x', s=50, linewidth=3)
    plt.plot(y_train, y_train, color='black', label='Train', linestyle='--')

    plt.xlabel('y_test')
    plt.ylabel('y_pred')
    plt.legend()

    if phase_name:
        plt.title(phase_name)

    plt.grid(True)
    plt.tight_layout()

    if save_path:
        plt.savefig(os.path.join(save_path, f'{name}.png'))
        plt.show()
        plt.close()
    else:
        plt.show()


def plot_comparison(phase_name, y_exp, y_nist, y_model, save_path=None, name=None):
    plt.figure(figsize=(8, 6))

    plt.scatter(y_exp, y_exp, color='black', label='Experimental', marker = 'x', s=50, linewidth=2)
    plt.scatter(y_exp, y_nist, color='blue', label='NIST', marker = '+', s=40,  linewidth=1)
    plt.scatter(y_exp, y_model, color='red', label='SVR', marker = '+', s=40, linewidth=1)

    plt.xlabel('Experimental')
    plt.ylabel('SVR & NIST')
    plt.title(phase_name)
    plt.legend()

    plt.grid(True)
    plt.tight_layout()

    if save_path:
        plt.savefig(os.path.join(save_path, f'{name}.png'))
        plt.show()
        plt.close()
    else:
        plt.show()

# ********************** PARAMETER DEFINITIONS **********************
properties = ("Therm. Cond. (W/m*K)")

'''
"Density (kg/m3)","Volume (m3/kg)",
"Internal Energy (kJ/mol)","Enthalpy (kJ/mol)","Entropy (J/molK)",
"Cv (J/molK)","Cp (J/molK)","Sound Spd. (m/s)","Joule-Thomson (K/MPa)",
"Viscosity (uPas)","Therm. Cond. (W/m*K)","Phase"
'''

## files and directories
#current_directory = os.getcwd()    #if used on the notebook
#from google.colab import drive
#drive.mount('/content/gdrive')
#current_directory = 'gdrive/MyDrive/Methane/'
current_directory = '/home/mmaximo/ML'    #if used on the cluster

# ********************** DATA ACQUISITION **********************
                     #*****  NIST  *****
            # **** Temperature, Pressure, Phase ****
'''
In this section, data from NIST is acquired for Temperature, Pressure, and the
corresponding physical state. These data are solely used to train a decision
tree to determine the phase in which the fluid exists at a given pressure and
temperature.
'''
NIST_directory = os.path.join(current_directory, "NIST")
txt_files_NIST = [file for file in os.listdir(NIST_directory) if file.endswith(".txt")]

X_NIST = []
state_column = []

for file in txt_files_NIST:
  df_NIST = pd.read_csv(os.path.join(NIST_directory, file), delimiter='\t')
  X_NIST_file = df_NIST[["Temperature (K)","Pressure (MPa)"]].values
  state_column_file = df_NIST.iloc[:, -1]  # Assuming the last column indicates the state

  X_NIST.extend(X_NIST_file)
  state_column.extend(state_column_file)

X_NIST = np.array(X_NIST)

# ***** DECISION TREE *****
DT_file = check_and_get_filename(current_directory, "DecisionTree_Physical-State-Determination_SVR", "log")

## Mapping of physical states. Associate them with numbers (0, 1, 2) for use in the decision tree
state_mapping = {'liquid': 0, 'vapor': 1, 'supercritical': 2}
state_mapped = [state_mapping[state] for state in state_column]

# Spliting the data into training (70%) and testing (30%) sets (better than 80-20)
X_train, X_test, state_train, state_test = train_test_split(X_NIST, state_mapped, test_size=0.3, random_state=42)

log_info = f"Decision tree to predict physical states based on temperature and pressure inputs.\nNumber of data: {len(X_NIST)}\nNumber of train data: {len(X_train)}\nNumber of test data: {len(X_test)}"
save_to_file_and_print(log_info, DT_file)

decision_tree = DecisionTreeClassifier(random_state=42)

decision_tree.fit(X_train, state_train)

state_pred = decision_tree.predict(X_test)

accuracy_tree = accuracy_score(state_test, state_pred)

save_to_file_and_print(f"\nAccuracy of Decision Tree model: {accuracy_tree * 100:.3f}%", DT_file)
save_to_file_and_print(classification_report(state_test, state_pred), DT_file)

# Metrics - Decision Tree Evaluation
save_to_file_and_print("\n\n > Decision Tree Evaluation <", DT_file)
calculate_metrics('Decision Tree Train', state_test, state_pred, ['RMSE', 'R2'], DT_file)

# ********************** DATA ACQUISITION **********************
            # **** Temperature, Pressure, Property ****

property = "Therm. Cond. (W/m*K)"
property_name = property.split(' (')[0]
print(f"\n\n*************Start analysis of property '{property_name}'*************")

property_directory = os.path.join(current_directory, property_name)
Experimental_directory = os.path.join(property_directory, "Experimental")

# ********************** SVR **********************

SVR_directory = os.path.join(property_directory, "SVR-cv10")
os.makedirs(SVR_directory, exist_ok=True)
SVR_file = check_and_get_filename(SVR_directory, "SVR-cv10", "log")

# *****  EXPERIMENTAL  *****

txt_files_Exp = [file for file in os.listdir(Experimental_directory) if file.endswith(".txt")]
y_Exp = []  ## Dependent variable for all states
X_Exp = []  ## Independent variables (Temperature and Pressure) for all states


for file_exp in txt_files_Exp:
    df_Exp = pd.read_csv(os.path.join(Experimental_directory, file_exp), delimiter='\t')
    X_Exp_file = df_Exp[["Temperature (K)","Pressure (MPa)"]].values
    y_Exp_file = df_Exp[property].values
    X_Exp.extend(X_Exp_file)
    y_Exp.extend(y_Exp_file)
X_Exp = np.array(X_Exp)
X_Exp=X_Exp.tolist()
if property == "Therm. Cond. (W/m*K)":
    y_Exp = [x * 1000 for x in  y_Exp]
else:
    pass
y_Exp = [[x] for x in  y_Exp]

# *****  NIST  *****
'''
NIST data that presents the same temperature and pressure conditions as those
used in the experimental data has been acquired.
'''
NIST_Expbased_directory = os.path.join(NIST_directory, "results_experimental-based")

txt_files_NIST_Expbased = [file for file in os.listdir(NIST_Expbased_directory) if file.endswith(".txt")]
y_NIST_Expbased = []  ## Dependent variable for all states
X_NIST_Expbased = []  ## Independent variables (Temperature and Pressure) for all states

for file_exp in txt_files_NIST_Expbased:
  df_NIST_Expbased = pd.read_csv(os.path.join(NIST_Expbased_directory, file_exp), delimiter='\t')
  X_NIST_Expbased_file = df_NIST_Expbased[["Temperature (K)","Pressure (MPa)"]].values
  y_NIST_Expbased_file = df_NIST_Expbased[property].values
  X_NIST_Expbased.extend(X_NIST_Expbased_file)
  y_NIST_Expbased.extend(y_NIST_Expbased_file)
'''
Since y_NIST_Expbased is a scalar value and y_NIST_Expbased is a NumPy array,
They cannot be accessed using indexing.
One possible solution is to convert it into a list.
'''
X_NIST_Expbased = np.array(X_NIST_Expbased)
X_NIST_Expbased=X_NIST_Expbased.tolist()
if property == "Therm. Cond. (W/m*K)":
  y_NIST_Expbased = [x * 1000 for x in  y_NIST_Expbased]
else:
  pass
y_NIST_Expbased = [[x] for x in  y_NIST_Expbased]
print(y_NIST_Expbased)

'''
Given that not all experimental data falls within the NIST range of Temperature
and pressure, the values that lie within the range are stored in a variable for
error analysis.
'''

missing_data_X = []
matched_data = []

for x_exp, y_exp in zip(X_Exp, y_Exp):
    if any(np.array_equal(x_exp, x_nist) for x_nist in X_NIST_Expbased):
        matched_data.append((x_exp, y_exp))
    else:
        missing_data_X.append(x_exp)

missing_data_y = [y for x, y in zip(X_Exp, y_Exp) if any(np.array_equal(x, x_nist) for x_nist in missing_data_X)]

matched_data_X = [x for x, _ in matched_data]
matched_data_y = [y for _, y in matched_data]

save_to_file_and_print(f"Number of matched data between NIST and Experimental: {len(matched_data_X)}\nNumber of missing data between NIST and Experimental: {len(missing_data_X)}", SVR_file)

X_liquid_Exp = []
y_liquid_Exp = []
X_vapor_Exp = []
y_vapor_Exp = []
X_supercritical_Exp = []
y_supercritical_Exp = []


#**** Discovering the physical state in the studied condition and separating the set****
#{'liquid': 0, 'vapor': 1, 'supercritical': 2}
state_pred_list_Exp_Expbased = decision_tree.predict(matched_data_X)

#Convert to a list type:
state_pred_list_Exp_Expbased = [[x] for x in state_pred_list_Exp_Expbased]


for i in range(len(state_pred_list_Exp_Expbased)):

  if state_pred_list_Exp_Expbased[i] == [0]:  # Liquid state
    X_liquid_Exp.append(matched_data_X[i])
    y_liquid_Exp.append(matched_data_y[i])
  elif state_pred_list_Exp_Expbased[i] == [1]:  # Vapor state
    X_vapor_Exp.append(matched_data_X[i])
    y_vapor_Exp.append(matched_data_y[i])
  elif state_pred_list_Exp_Expbased[i] == [2]:  # Supercritical state
    X_supercritical_Exp.append(matched_data_X[i])
    y_supercritical_Exp.append(matched_data_y[i])

print(f"Number of data points in Liquid state: {len(X_liquid_Exp)}")
print(f"Number of data points in Vapor state: {len(X_vapor_Exp)}")
print(f"Number of data points in Supercritical state: {len(X_supercritical_Exp)}")

# Lists to store corresponding NIST data for each phase
y_liquid_NIST_Expbased = []
y_vapor_NIST_Expbased = []
y_supercritical_NIST_Expbased = []
X_liquid_NIST_Expbased = []
X_vapor_NIST_Expbased = []
X_supercritical_NIST_Expbased = []

# For Liquid Phase
for x_exp in X_liquid_Exp:
    for i, x_nist in enumerate(X_NIST_Expbased):
        if np.array_equal(x_exp, x_nist):
            X_liquid_NIST_Expbased.append(x_nist)
            y_liquid_NIST_Expbased.append(y_NIST_Expbased[i])
            break

# For Vapor Phase
for x_exp in X_vapor_Exp:
    for i, x_nist in enumerate(X_NIST_Expbased):
        if np.array_equal(x_exp, x_nist):
            X_vapor_NIST_Expbased.append(x_nist)
            y_vapor_NIST_Expbased.append(y_NIST_Expbased[i])
            break

# For Supercritical Phase
for x_exp in X_supercritical_Exp:
    for i, x_nist in enumerate(X_NIST_Expbased):
        if np.array_equal(x_exp, x_nist):
            X_supercritical_NIST_Expbased.append(x_nist)
            y_supercritical_NIST_Expbased.append(y_NIST_Expbased[i])
            break

print(f"Data size in liquid phase (NIST): {len(X_liquid_NIST_Expbased)}, Corresponding experimental data: {len(X_liquid_Exp)}")
print(f"Data size in vapor phase (NIST): {len(X_vapor_NIST_Expbased)}, Corresponding experimental data: {len(X_vapor_Exp)}")
print(f"Data size in supercritical phase (NIST): {len(X_supercritical_NIST_Expbased)}, Corresponding experimental data: {len(X_supercritical_Exp)}")




#           >>>>>       LIQUID PART     <<<<<
if len(X_liquid_Exp) > 0:
    save_to_file_and_print("\n\n>>> LIQUID PHASE <<<\n", SVR_file)
    # Spliting the data into training (80%) and testing (20%) sets for liquid state
    X_liquid_train, X_liquid_test, y_liquid_train, y_liquid_test = train_test_split(X_liquid_Exp, y_liquid_Exp, test_size=0.2, random_state=42)

    grid_search_liquid = GridSearchCV(
    SVR(),
    param_grid = {
        'kernel': ['poly'],
        'C': [5, 10],
        'epsilon': [0.1, 0.2],
        'gamma': ['scale'],
        'degree': [2, 3, 4]
            },
    cv = 10,
    scoring='neg_mean_squared_error',
    verbose=0,
    n_jobs=-1
    )


    grid_search_liquid.fit(X_liquid_train, y_liquid_train)

    save_to_file_and_print(f"\nBest Hyperparameters for liquid state for SVR: {grid_search_liquid.best_params_}.\n", SVR_file)

    model_liquid = grid_search_liquid.best_estimator_
    model_liquid.fit(X_liquid_train, y_liquid_train)

    joblib.dump(model_liquid, os.path.join(SVR_directory, 'Model_SVR_liquid.pkl'))

    #model_liquid_path = os.path.join(SVR_directory, 'Model_SVR_liquid.pkl')
    #model_liquid = joblib.load(model_liquid_path)

    # Metrics - Model Evaluation

    y_pred_test_liquid = model_liquid.predict(X_liquid_test)
    y_pred_train_liquid = model_liquid.predict(X_liquid_train)

    # >>> Train <<<
    save_to_file_and_print("\n > Train data <", SVR_file)
    calculate_metrics('liquid', y_liquid_train, y_pred_train_liquid, file=SVR_file)

    # >>> Test <<<
    save_to_file_and_print("\n > Test data <", SVR_file)
    calculate_metrics('liquid', y_liquid_test,  y_pred_test_liquid, file=SVR_file)

    plot_overfitting_evaluation(y_liquid_test, y_pred_test_liquid, save_path=SVR_directory, name="SVR-overfitting_evaluation-liquid", phase_name="liquid")

    y_liquid_Exp_array = np.array(y_liquid_Exp)
    y_liquid_NIST_Expbased_array = np.array(y_liquid_NIST_Expbased)
    y_pred_liquid_cv_array = np.array(cross_val_predict(model_liquid, X_liquid_Exp, y_liquid_Exp, cv = 10))

    liquid_score = cross_val_score(model_liquid, X_liquid_Exp, y_liquid_Exp, cv = 10, scoring='neg_root_mean_squared_error')
    liquid_cv_mean = np.mean(liquid_score)
    liquid_cv_std = np.std(liquid_score)

    save_to_file_and_print(f"*** Cross-Validation Metrics ***    Liquid Phase - RMSE (mean): {-liquid_cv_mean}\nRMSE (std): {liquid_cv_std}\n", SVR_file)

    #liquid
    save_to_file_and_print(">>> Comparison: Liquid <<<\n", SVR_file)
    calculate_metrics("liquid - Exp x NIST", y_liquid_Exp_array, y_liquid_NIST_Expbased_array, file=SVR_file)
    calculate_metrics("liquid - Exp x Model", y_liquid_Exp_array, y_pred_liquid_cv_array, file=SVR_file)
    calculate_metrics("liquid - NIST x Model", y_liquid_NIST_Expbased_array, y_pred_liquid_cv_array, file=SVR_file)

    # Liquid phase
    plot_comparison("liquid", y_liquid_Exp_array, y_liquid_NIST_Expbased_array, y_pred_liquid_cv_array, save_path=SVR_directory, name="ModelxNISTxExp-liquid")
    plot_overfitting_evaluation(y_liquid_NIST_Expbased_array, y_pred_liquid_cv_array, save_path=SVR_directory, name="ModelxNIST-liquid", phase_name='Liquid')

    liquid_data = np.column_stack((X_liquid_Exp, y_liquid_Exp_array, y_liquid_NIST_Expbased_array, y_pred_liquid_cv_array))
    np.savetxt(os.path.join(SVR_directory, 'liquid_data.txt'), liquid_data, delimiter='\t', header='Temp(K)\tPressure(MPa)\tExperimental(mW/m*K)\tNIST(mW/m*K)\tModel(mW/m*K)')



#           >>>>>       VAPOR PART     <<<<<
if len(X_vapor_Exp) > 0:
    save_to_file_and_print("\n\n>>> VAPOR PHASE <<<\n", SVR_file)
    # Spliting the data into training (80%) and testing (20%) sets for vapor state
    X_vapor_train, X_vapor_test, y_vapor_train, y_vapor_test = train_test_split(X_vapor_Exp, y_vapor_Exp, test_size=0.2, random_state=42)

    grid_search_vapor = GridSearchCV(
    SVR(),
    param_grid = {
        'kernel': ['poly'],
        'C': [5, 10],
        'epsilon': [0.1, 0.2],
        'gamma': ['scale'],
        'degree': [2, 3, 4]
            },
    cv = 10,
    scoring='neg_mean_squared_error',
    verbose=0,
    n_jobs=-1
    )


    grid_search_vapor.fit(X_vapor_train, y_vapor_train)

    save_to_file_and_print(f"\nBest Hyperparameters for vapor state for SVR: {grid_search_vapor.best_params_}.\n", SVR_file)

    model_vapor = grid_search_vapor.best_estimator_
    model_vapor.fit(X_vapor_train, y_vapor_train)

    joblib.dump(model_vapor, os.path.join(SVR_directory, 'Model_SVR_vapor.pkl'))

    #model_vapor_path = os.path.join(SVR_directory, 'Model_SVR_vapor.pkl')
    #model_vapor = joblib.load(model_vapor_path)

    # Metrics - Model Evaluation

    y_pred_test_vapor = model_vapor.predict(X_vapor_test)
    y_pred_train_vapor = model_vapor.predict(X_vapor_train)

    # >>> Train <<<
    save_to_file_and_print("\n > Train data <", SVR_file)
    calculate_metrics('vapor', y_vapor_train, y_pred_train_vapor, file=SVR_file)

    # >>> Test <<<
    save_to_file_and_print("\n > Test data <", SVR_file)
    calculate_metrics('vapor', y_vapor_test,  y_pred_test_vapor, file=SVR_file)

    plot_overfitting_evaluation(y_vapor_test, y_pred_test_vapor, save_path=SVR_directory, name="SVR-overfitting_evaluation-vapor", phase_name="vapor")

    y_vapor_Exp_array = np.array(y_vapor_Exp)
    y_vapor_NIST_Expbased_array = np.array(y_vapor_NIST_Expbased)
    y_pred_vapor_cv_array =  np.array(cross_val_predict(model_vapor, X_vapor_Exp, y_vapor_Exp, cv = 10))

    vapor_score = cross_val_score(model_vapor, X_vapor_Exp, y_vapor_Exp, cv = 10, scoring='neg_root_mean_squared_error')
    vapor_cv_mean = np.mean(vapor_score)
    vapor_cv_std = np.std(vapor_score)

    save_to_file_and_print(f"*** Cross-Validation Metrics ***    Vapor Phase - RMSE (mean): {-vapor_cv_mean}\nRMSE (std): {vapor_cv_std}\n", SVR_file)

    #vapor
    save_to_file_and_print(">>> Vapor <<<\n", SVR_file)
    calculate_metrics("vapor - Exp x NIST", y_vapor_Exp_array, y_vapor_NIST_Expbased_array, file=SVR_file)
    calculate_metrics("vapor - Exp x Model", y_vapor_Exp_array, y_pred_vapor_cv_array, file=SVR_file)
    calculate_metrics("vapor - NIST x Model", y_vapor_NIST_Expbased_array, y_pred_vapor_cv_array, file=SVR_file)

    # Vapor phase
    plot_comparison("vapor",  y_vapor_Exp_array, y_vapor_NIST_Expbased_array, y_pred_vapor_cv_array, save_path=SVR_directory, name="ModelxNISTxExp-vapor")
    plot_overfitting_evaluation(y_vapor_NIST_Expbased_array, y_pred_vapor_cv_array, save_path=SVR_directory, name="ModelxNIST-vapor", phase_name='Vapor')

    vapor_data = np.column_stack((X_vapor_Exp, y_vapor_Exp_array, y_vapor_NIST_Expbased_array, y_pred_vapor_cv_array))
    np.savetxt(os.path.join(SVR_directory, 'vapor_data.txt'), vapor_data, delimiter='\t', header='Temp(K)\tPressure(MPa)\tExperimental(mW/m*K)\tNIST(mW/m*K)\tModel(mW/m*K)')


#           >>>>>       SUPERCRITICAL PART     <<<<<
if len(X_supercritical_Exp) > 0:
    save_to_file_and_print("\n\n>>> SUPERCRITICAL PHASE <<<\n", SVR_file)
    # Spliting the data into training (80%) and testing (20%) sets for supercritical state
    X_supercritical_train, X_supercritical_test, y_supercritical_train, y_supercritical_test = train_test_split(X_supercritical_Exp, y_supercritical_Exp, test_size=0.2, random_state=42)

    grid_search_supercritical = GridSearchCV(
    SVR(),
    param_grid = {
        'kernel': ['poly'],
        'C': [5, 10],
        'epsilon': [0.1, 0.2],
        'gamma': ['scale'],
        'degree': [2, 3, 4]
            },
    cv = 10,
    scoring='neg_mean_squared_error',
    verbose=0,
    n_jobs=-1
    )


    grid_search_supercritical.fit(X_supercritical_train, y_supercritical_train)

    save_to_file_and_print(f"\nBest Hyperparameters for supercritical state for SVR: {grid_search_supercritical.best_params_}.\n", SVR_file)

    model_supercritical = grid_search_supercritical.best_estimator_
    model_supercritical.fit(X_supercritical_train, y_supercritical_train)
    joblib.dump(model_supercritical, os.path.join(SVR_directory, 'Model_SVR_supercritical.pkl'))

    #model_supercritical_path = os.path.join(SVR_directory, 'Model_SVR_supercritical.pkl')
    #model_supercritical = joblib.load(model_supercritical_path)

    # Metrics - Model Evaluation

    y_pred_test_supercritical = model_supercritical.predict(X_supercritical_test)
    y_pred_train_supercritical = model_supercritical.predict(X_supercritical_train)

    # >>> Train <<<
    save_to_file_and_print("\n > Train data <", SVR_file)
    calculate_metrics('supercritical', y_supercritical_train, y_pred_train_supercritical, file=SVR_file)

    # >>> Test <<<
    save_to_file_and_print("\n > Test data <", SVR_file)
    calculate_metrics('supercritical', y_supercritical_test,  y_pred_test_supercritical, file=SVR_file)

    plot_overfitting_evaluation(y_supercritical_test, y_pred_test_supercritical, save_path=SVR_directory, name="SVR-overfitting_evaluation-supercritical", phase_name="supercritical")


    y_supercritical_Exp_array = np.array(y_supercritical_Exp)
    y_supercritical_NIST_Expbased_array = np.array(y_supercritical_NIST_Expbased)
    y_pred_supercritical_cv_array = np.array(cross_val_predict(model_supercritical, X_supercritical_Exp, y_supercritical_Exp, cv = 10))

    supercritical_score = cross_val_score(model_supercritical, X_supercritical_Exp, y_supercritical_Exp, cv = 10, scoring='neg_root_mean_squared_error')
    supercritical_cv_mean = np.mean(supercritical_score)
    supercritical_cv_std = np.std(supercritical_score)

    save_to_file_and_print(f"*** Cross-Validation Metrics ***    Supercritical Phase - RMSE (mean): {-supercritical_cv_mean}\nRMSE (std): {supercritical_cv_std}\n\n\n", SVR_file)

    save_to_file_and_print(">>> Supercritical <<<\n", SVR_file)
    calculate_metrics("supercritical - Exp x NIST", y_supercritical_Exp_array, y_supercritical_NIST_Expbased_array, file=SVR_file)
    calculate_metrics("supercritical - Exp x Model", y_supercritical_Exp_array, y_pred_supercritical_cv_array, file=SVR_file)
    calculate_metrics("supercritical - NIST x Model", y_supercritical_NIST_Expbased_array, y_pred_supercritical_cv_array, file=SVR_file)

    plot_comparison("supercritical", y_supercritical_Exp_array, y_supercritical_NIST_Expbased_array, y_pred_supercritical_cv_array, save_path=SVR_directory, name="ModelxNISTxExp-supercritical")
    plot_overfitting_evaluation(y_supercritical_NIST_Expbased_array, y_pred_supercritical_cv_array, save_path=SVR_directory, name="ModelxNIST-Supercritical", phase_name='Supercritical')

    supercritical_data = np.column_stack((X_supercritical_Exp, y_supercritical_Exp_array, y_supercritical_NIST_Expbased_array, y_pred_supercritical_cv_array))
    np.savetxt(os.path.join(SVR_directory, 'supercritical_data.txt'), supercritical_data, delimiter='\t', header='Temp(K)\tPressure(MPa)\tExperimental(mW/m*K)\tNIST(mW/m*K)\tModel(mW/m*K)')

