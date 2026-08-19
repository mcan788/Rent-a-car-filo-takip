import pyodbc, datetime
conn = pyodbc.connect(r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=TUR_TAKIP_DEMO_DB;Trusted_Connection=yes;')
cr = conn.cursor()

today = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Insert 5 bookings for today
cr.execute("""
INSERT INTO Bookings (TourID, OfficeID, TouristName, HotelName, AdultCount, ChildCount, BabyCount, PassengerCount, DriverCount, VehicleCount, ActualPassFee, Earnings, Currency, Notes, BookingDate) VALUES
(4, 1, 'Bugunku Musteri 1', 'Titanic Hotel', 2, 0, 0, 2, 0, 0, 45.00, 150.00, 'TL', 'Bugun Demo', ?),
(4, 1, 'Bugunku Musteri 2', 'Rixos Hotel', 4, 1, 0, 5, 0, 0, 45.00, 300.00, 'TL', 'Bugun Demo', ?),
(4, 1, 'Bugunku Musteri 3', 'Maxx Royal', 2, 0, 0, 2, 0, 0, 45.00, 150.00, 'TL', 'Bugun Demo', ?),
(4, 1, 'Bugunku Musteri 4', 'Regnum Carya', 1, 0, 0, 1, 0, 0, 45.00, 75.00, 'TL', 'Bugun Demo', ?),
(4, 1, 'Bugunku Musteri 5', 'Sueno Hotel', 3, 0, 0, 3, 0, 0, 45.00, 225.00, 'TL', 'Bugun Demo', ?)
""", (today, today, today, today, today))
conn.commit()
print('Added 5 bookings for today!')
