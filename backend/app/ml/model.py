import tensorflow as tf
from tensorflow import keras
from keras import layers

def build_lstm_model(lookback: int = 60, units_layer1: int = 64, units_layer2: int = 32, dropout_rate: float = 0.2) -> keras.Model:
    """
    Constructs a 2-layer stacked LSTM neural network with Dropout and Dense output.
    Architecture:
      Input (lookback, 1)
      LSTM (units_layer1, return_sequences=True)
      Dropout (dropout_rate)
      LSTM (units_layer2, return_sequences=False)
      Dropout (dropout_rate)
      Dense (16, activation='relu')
      Dense (1, activation='linear')
    """
    model = keras.Sequential([
        layers.Input(shape=(lookback, 1)),
        layers.LSTM(units_layer1, return_sequences=True),
        layers.Dropout(dropout_rate),
        layers.LSTM(units_layer2, return_sequences=False),
        layers.Dropout(dropout_rate),
        layers.Dense(16, activation="relu"),
        layers.Dense(1, activation="linear")
    ])

    optimizer = keras.optimizers.Adam(learning_rate=0.001)
    model.compile(optimizer=optimizer, loss="mean_squared_error", metrics=["mae"])
    return model
