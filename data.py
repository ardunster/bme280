import datetime
import math
import sqlite3
import time

# Allow code testing on non i2c systems:
try:
    import adafruit_bme280
    import board
    import busio
except NotImplementedError:
    print("No valid board detected.")


class FakeBME:
    """
    Used for testing various code on systems without a bme280 sensor
    """

    temperature = 30.0
    humidity = 75
    pressure = 1013.25


def connections_setup():
    global i2c
    global bme280
    global dbconn
    global dbcursor
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
        dbconn = sqlite3.connect("readings.db")
        dbcursor = dbconn.cursor()


def table_setup():
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
    insert_command = "INSERT INTO readings VALUES (?, ?, ?, ?, ?, ?)"

    dbcursor.execute(
        insert_command,
        [temp_f, humidity, pressure, dewpoint, dtoutput[0], dtoutput[1]],
    )

    dbconn.commit()
    time = datetime.datetime.strptime(
        (dtoutput[0] + dtoutput[1]), "%Y%m%d%H%M%S"
        )
    print(
        f"Saved at: {time}: "
        f"Temp: {temp_f}, Humidity: {humidity}, Pressure: {pressure}"
    )


def read_db():
    dbcursor.execute("SELECT * FROM readings")
    results = dbcursor.fetchall()
    return results


if __name__ == "__main__":
    connections_setup()
    table_setup()

    while True:
        try:
            write_data(*get_data(), get_datetime())
            time.sleep(60)
        except KeyboardInterrupt:
            print("Exiting...")
            break

    print(read_db())

    print(dbconn.total_changes)

    dbconn.commit()
    dbcursor.close()
    dbconn.close()
