import datetime
import math
import sqlite3
import time

# Allow other code to be tested on non i2c enabled systems
try:
    import adafruit_bme280
    import board
    import busio
except NotImplementedError:
    print("No valid board detected.")


class FakeBME:
    """
    Used for testing non-sensor related code on systems without a bme280 sensor.
    """

    temperature = 30.0
    humidity = 75
    pressure = 1013.25


def connections_setup():
    global i2c
    global bme280
    global dbconn
    global dbcursor

    # If sensor connection cannot be loaded correctly, uses the dummy item instead.
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)
    except Exception as exception:
        print(
            f"Cannot create sensor object: {exception}"
            "\n--Using testing object instead."
        )
        i2c = None
        bme280 = FakeBME()
    finally:
        # Set up sqlite connection regardless.
        dbconn = sqlite3.connect("readings.db")
        dbcursor = dbconn.cursor()


def table_setup():
    """
    Create the table to store readings. Report error if any (typically reports
    table already exists.)
    """
    create_table = (
        "CREATE TABLE readings (temperature REAL, humidity REAL, "
        "pressure REAL, dewpoint REAL, date INTEGER, time INTEGER)"
    )
    try:
        dbcursor.execute(create_table)
    except sqlite3.OperationalError as err:
        print(f"Can't create table: {err}")
        print("Continuing...")


def get_data():
    """
    Retrieves data from sensor, calculates conversion to Fahrenheit, calculates
    current dew point, returns data.
    """
    temp_f = (bme280.temperature * 1.8) + 32
    humidity = bme280.humidity
    pressure = bme280.pressure

    # Dew Point Calculation
    b = 17.62
    c = 243.12
    gamma = (b * bme280.temperature / (c + bme280.temperature)) + math.log(
        bme280.humidity / 100.0
    )
    dewpoint = (c * gamma) / (b - gamma)

    return temp_f, humidity, pressure, dewpoint


def get_datetime():
    """
    Gets current datetime and converts to integers for storage
    """
    dt = datetime.datetime.now()
    dtoutput = []
    dtoutput.append(dt.strftime("%Y%m%d"))
    dtoutput.append(dt.strftime("%H%M%S"))

    return dtoutput


def write_data(temp_f, humidity, pressure, dewpoint, dtoutput):
    """
    Writes the data to the sqlite table.
    """
    insert_command = "INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?)"

    dbcursor.execute(
        insert_command,
        [temp_f, humidity, pressure, dewpoint, dtoutput[0], dtoutput[1]],
    )

    # Commit changes in function in case of unexpected program exit.
    dbconn.commit()
    time = datetime.datetime.strptime((dtoutput[0] + dtoutput[1]), "%Y%m%d%H%M%S")
    print(
        f"Saved at: {time}: "
        f"Temp: {temp_f}, Humidity: {humidity}, Pressure: {pressure}"
    )


def read_db():
    """
    Gets all data from sqlite table.
    """
    dbcursor.execute("SELECT * FROM readings")
    results = dbcursor.fetchall()
    return results


def read_db_one():
    """
    Gets most recent line from sqlite table.
    """
    dbcursor.execute("SELECT * FROM readings ORDER BY date DESC, time DESC")
    results = dbcursor.fetchone()
    return results


if __name__ == "__main__":
    # Attempt to set up connections and create the table.
    connections_setup()
    table_setup()

    # Get data once without recording due to sensor anomolies
    get_data()

    # Then start the sensor recording loop.
    while True:
        try:
            write_data(*get_data(), get_datetime())
            time.sleep(60)
        except KeyboardInterrupt:
            print("Exiting...")
            break

    # Save any lingering changes and close database connections before exit.
    dbconn.commit()
    dbcursor.close()
    dbconn.close()
