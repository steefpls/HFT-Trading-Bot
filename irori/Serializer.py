import json

# Global variable to hold the backtesting flag and in-memory storage
backtest_mode = False
in_memory_storage = {}

def setup_backtest():
    """
    Enable backtesting mode. When enabled, serialization and deserialization
    will operate in memory instead of using a file.
    
    :param enable: Boolean to enable or disable backtesting mode (default: True).
    """
    global backtest_mode
    backtest_mode = True
    if backtest_mode:
        print("Backtesting mode enabled.")

def serialize_to_dat(var_name, data, data_type):
    """
    Serialize the given variable into a .dat file using JSON format or store in memory during backtest.
    
    :param var_name: The name of the variable to serialize.
    :param data: The value of the variable to serialize.
    :param data_type: The data type of the variable (e.g., int, str, list, etc.).
    """
    global in_memory_storage
    serialized_data = {
        "name": var_name,
        "type": data_type.__name__,
        "value": data
    }
    
    filename = 'data.dat'
    
    if backtest_mode:
        # Store the serialized data in memory
        in_memory_storage[var_name] = serialized_data
        #print(f"Data successfully serialized in-memory for variable '{var_name}'.")
    else:
        try:
            # Load existing data if available
            with open(filename, 'r') as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            existing_data = {}  # No existing data found, create an empty dictionary

        # Update the existing data with the new variable
        existing_data[var_name] = serialized_data
        
        # Store the updated data in the file
        with open(filename, 'w') as f:
            json.dump(existing_data, f)
        #print(f"Data successfully serialized to {filename} for variable '{var_name}'.")

def deserialize_from_dat(var_name, data_type, default_value):
    """
    Deserialize the variable from the .dat file or from memory during backtest.
    
    :param var_name: The name of the variable to deserialize.
    :param data_type: The expected data type for deserialization.
    :param default_value: The value to return if the variable or file doesn't exist.
    :return: The deserialized variable or the default_value if file/variable not found.
    """
    global in_memory_storage
    global backtest_mode  # Assuming backtest_mode is defined globally
    
    filename = 'data.dat'
    
    if backtest_mode:
        # Retrieve the serialized data from memory
        if var_name not in in_memory_storage:
            return default_value  # Return the default value if not found
        serialized_data = in_memory_storage[var_name]
    else:
        try:
            # Load all serialized data from the file
            with open(filename, 'r') as f:
                existing_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default_value  # Return the default value if the file is not found
        
        # Check if the specific variable exists in the loaded data
        if var_name not in existing_data:
            return default_value
        
        serialized_data = existing_data[var_name]

    # Ensure the variable name and data type match the expected type
    if serialized_data['type'] != data_type.__name__:
        raise TypeError(f"Expected type {data_type.__name__}, but got {serialized_data['type']}.")

    return data_type(serialized_data['value'])

# # Example usage:
# # Enable backtest mode
# setup_backtest(True)

# # Serialize an integer in backtest mode
# serialize_to_dat(123, int)

# # Deserialize it back in backtest mode
# result = deserialize_from_dat(int)
# print("Deserialized value:", result)

# # Disable backtest mode
# setup_backtest(False)

# # Now, serialize and deserialize to and from a file
# serialize_to_dat(456, int)
# result = deserialize_from_dat(int)
# print("Deserialized value from file:", result)
