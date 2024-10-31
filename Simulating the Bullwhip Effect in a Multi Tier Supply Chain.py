# **Simulating the Bullwhip Effect in a Multi-Tier Supply Chain**

# Settings
"""

# Define cost per unit for storage and backorder penalties
STORAGE_COST_PER_UNIT = 0.5        # Cost incurred for storing each unit of product
BACKORDER_PENALTY_COST_PER_UNIT = 1 # Cost penalty for each unit in backorder (unfulfilled orders)

# Define the number of weeks for the simulation
WEEKS_TO_PLAY = 41                 # Total simulation period in weeks

# Set delay in supply chain (in weeks)
QUEUE_DELAY_WEEKS = 2              # Delay time in weeks between order and delivery in supply chain

# Initial values for various stock-related metrics
INITIAL_STOCK = 12                 # Starting stock level for each actor
INITIAL_COST = 0                   # Initial cost at the beginning of the simulation
INITIAL_CURRENT_ORDERS = 0         # Initial orders at the start of the simulation

# Customer ordering pattern settings
CUSTOMER_INITIAL_ORDERS = 5        # Initial order quantity for customers in early weeks
CUSTOMER_SUBSEQUENT_ORDERS = 9     # Increased order quantity for customers in subsequent weeks

# Target stock level for supply chain actors
TARGET_STOCK = 12                  # Desired stock level to balance demand and minimize costs

"""# Customers"""

# Define the Customer class to simulate customer behavior
class Customer:
    def __init__(self):
        # Initialize the total beer received by the customer
        self.totalBeerReceived = 0
        return

    def RecieveFromRetailer(self, amountReceived):
        # Update the total amount of beer received based on supply from the retailer
        self.totalBeerReceived += amountReceived
        return

    def CalculateOrder(self, weekNum):
        # Calculate the customer order based on the week number
        # Order amount changes after the initial weeks to reflect demand increase
        if weekNum <= 5:
            result = CUSTOMER_INITIAL_ORDERS
        else:
            result = CUSTOMER_SUBSEQUENT_ORDERS
        return result

    def GetBeerReceived(self):
        # Retrieve the total amount of beer received by the customer
        return self.totalBeerReceived

"""# SupplyChainQueue"""

class SupplyChainQueue:

    def __init__(self, queueLength):
        # Initialize the supply chain queue with a specified length
        # 'queueLength' represents the maximum number of orders that can be held in the queue
        self.queueLength = queueLength
        self.data = []                  # List to store orders in the queue
        return

    def PushEnvelope(self, numberOfCasesToOrder):
        # Attempt to place a new order in the queue
        # 'numberOfCasesToOrder' represents the quantity of product ordered
        orderSuccessfullyPlaced = False  # Track if order was successfully added

        if len(self.data) < self.queueLength:  # Check if queue has space for the order
            self.data.append(numberOfCasesToOrder)  # Add order to the queue
            orderSuccessfullyPlaced = True          # Mark order as successfully placed

        return orderSuccessfullyPlaced  # Return whether the order was successfully added

    def AdvanceQueue(self):
        # Move the queue forward by removing the oldest order (FIFO - First In, First Out)
        # This simulates the delay in processing orders over time
        self.data.pop(0)  # Remove the first order in the queue
        return

    def PopEnvelope(self):
        # Retrieve the next order to be delivered from the front of the queue
        if len(self.data) >= 1:         # Check if there is at least one order in the queue
            quantityDelivered = self.data[0]  # Get the first order in the queue
            self.AdvanceQueue()               # Remove it from the queue after delivery
        else:
            quantityDelivered = 0       # No orders to deliver if the queue is empty

        return quantityDelivered        # Return the quantity to be delivered

    def PrettyPrint(self):
        # Print the current state of the queue, mainly for debugging purposes
        print(self.data)
        return

"""# SupplyChainActor"""

class SupplyChainActor:

    def __init__(self, incomingOrdersQueue, outgoingOrdersQueue, incomingDeliveriesQueue, outgoingDeliveriesQueue):
        # Initialize stock, orders, and cost attributes
        self.currentStock = INITIAL_STOCK              # Initial stock level for the actor
        self.currentOrders = INITIAL_CURRENT_ORDERS    # Initial orders to be fulfilled
        self.costsIncurred = INITIAL_COST              # Initial cost at the start of the simulation

        # Set up queues for managing orders and deliveries
        self.incomingOrdersQueue = incomingOrdersQueue   # Queue for orders from downstream actors
        self.outgoingOrdersQueue = outgoingOrdersQueue   # Queue for orders to upstream actors
        self.incomingDeliveriesQueue = incomingDeliveriesQueue  # Queue for deliveries from upstream
        self.outgoingDeliveriesQueue = outgoingDeliveriesQueue  # Queue for deliveries to downstream

        self.lastOrderQuantity = 0  # Store the quantity ordered in the last round for tracking purposes
        return

    def PlaceOutgoingDelivery(self, amountToDeliver):
        # Place the calculated delivery quantity in the outgoing deliveries queue
        self.outgoingDeliveriesQueue.PushEnvelope(amountToDeliver)
        return

    def PlaceOutgoingOrder(self, weekNum):
        # Place an order based on the week number, using an "anchor and maintain" strategy after an initial period
        if weekNum <= 4:
            amountToOrder = 4  # Initial equilibrium order amount for the first few weeks
        else:
            # After initial weeks, determine order based on current orders and stock levels
            amountToOrder = 0.5 * self.currentOrders  # Order amount scales with outstanding orders

            # Adjust order to reach target stock level
            if (TARGET_STOCK - self.currentStock) > 0:
                amountToOrder += TARGET_STOCK - self.currentStock

        # Add the order to the outgoing orders queue
        self.outgoingOrdersQueue.PushEnvelope(amountToOrder)
        self.lastOrderQuantity = amountToOrder  # Track the last order quantity for reference
        return

    def ReceiveIncomingDelivery(self):
        # Receive a delivery from upstream by popping the first item in the incoming deliveries queue
        quantityReceived = self.incomingDeliveriesQueue.PopEnvelope()

        # Add the received quantity to the current stock
        if quantityReceived > 0:
            self.currentStock += quantityReceived
        return

    def ReceiveIncomingOrders(self):
        # Receive an order from downstream by popping the first item in the incoming orders queue
        thisOrder = self.incomingOrdersQueue.PopEnvelope()

        # Add the incoming order to the current orders to be fulfilled
        if thisOrder > 0:
            self.currentOrders += thisOrder
        return

    def CalcBeerToDeliver(self):
        # Calculate the quantity of beer to deliver based on current stock and orders
        deliveryQuantity = 0

        # If current stock can fulfill all current orders, deliver the full amount
        if self.currentStock >= self.currentOrders:
            deliveryQuantity = self.currentOrders
            self.currentStock -= deliveryQuantity    # Reduce stock by delivered quantity
            self.currentOrders -= deliveryQuantity    # Reduce outstanding orders accordingly
        # If stock is insufficient, deliver as much as possible and backorder the rest
        elif self.currentStock > 0 and self.currentStock < self.currentOrders:
            deliveryQuantity = self.currentStock      # Deliver all available stock
            self.currentStock = 0                     # Stock becomes zero after delivery
            self.currentOrders -= deliveryQuantity    # Reduce outstanding orders by delivered amount
        return deliveryQuantity

    def CalcCostForTurn(self):
        # Calculate the costs for the current turn, including storage and backorder penalties
        inventoryStorageCost = self.currentStock * STORAGE_COST_PER_UNIT  # Cost for holding inventory
        backorderPenaltyCost = self.currentOrders * BACKORDER_PENALTY_COST_PER_UNIT  # Cost for unfulfilled orders
        costsThisTurn = inventoryStorageCost + backorderPenaltyCost       # Total cost for this turn
        return costsThisTurn

    def GetCostIncurred(self):
        # Return the total costs incurred by this actor so far
        return self.costsIncurred

    def GetLastOrderQuantity(self):
        # Return the quantity of the last order placed by this actor
        return self.lastOrderQuantity

    def CalcEffectiveInventory(self):
        # Calculate effective inventory as the difference between stock and outstanding orders
        # This helps determine if the actor is in surplus or backorder
        return (self.currentStock - self.currentOrders)

"""# Retailer"""

class Retailer(SupplyChainActor):

    def __init__(self, incomingOrdersQueue, outgoingOrdersQueue, incomingDeliveriesQueue, outgoingDeliveriesQueue, theCustomer):
        # Initialize the retailer with supply chain queues and a customer instance
        # Inherit attributes and methods from the SupplyChainActor superclass
        super().__init__(incomingOrdersQueue, outgoingOrdersQueue, incomingDeliveriesQueue, outgoingDeliveriesQueue)
        self.customer = theCustomer  # Customer instance associated with the retailer
        return

    def ReceiveIncomingOrderFromCustomer(self, weekNum):
        # Add the calculated customer order for the current week to the retailer's orders
        # CalculateOrder method from Customer class is used to get the order amount
        self.currentOrders += self.customer.CalculateOrder(weekNum)
        return

    def ShipOutgoingDeliveryToCustomer(self):
        # Ship the calculated amount of beer to the customer by calling CalcBeerToDeliver
        # RecieveFromRetailer method from Customer class is used to receive the quantity delivered
        self.customer.RecieveFromRetailer(self.CalcBeerToDeliver())
        return

    def TakeTurn(self, weekNum):
        # Define the series of actions the retailer performs each turn (weekly):

        # 1. Receive new delivery from the wholesaler
        # This step also advances the delivery queue by removing the first order in line
        self.ReceiveIncomingDelivery()

        # 2. Receive new order from the customer
        self.ReceiveIncomingOrderFromCustomer(weekNum)

        # 3. Calculate and ship the required amount to the customer
        # Directly call RecieveFromRetailer with a fixed delivery amount for the initial weeks
        if weekNum <= 4:
            self.customer.RecieveFromRetailer(4)  # Fixed delivery amount in the first weeks
        else:
            self.customer.RecieveFromRetailer(self.CalcBeerToDeliver())  # Dynamic delivery based on stock

        # 4. Place an outgoing order to the wholesaler
        self.PlaceOutgoingOrder(weekNum)

        # 5. Update the retailer's costs for the current turn
        self.costsIncurred += self.CalcCostForTurn()
        return

"""# Wholesaler"""

class Wholesaler(SupplyChainActor):

    def __init__(self, incomingOrdersQueue, outgoingOrdersQueue, incomingDeliveriesQueue, outgoingDeliveriesQueue):
        # Initialize the wholesaler with supply chain queues by inheriting from SupplyChainActor
        super().__init__(incomingOrdersQueue, outgoingOrdersQueue, incomingDeliveriesQueue, outgoingDeliveriesQueue)
        return

    def TakeTurn(self, weekNum):
        # Define the steps the wholesaler performs each turn (weekly):

        # 1. Receive new delivery from the distributor
        # This step also advances the delivery queue by removing the first order in line
        self.ReceiveIncomingDelivery()

        # 2. Receive new order from the retailer
        # This step also advances the orders queue
        self.ReceiveIncomingOrders()

        # 3. Prepare and place the outgoing delivery to the retailer
        # Initially, for the first few weeks, send a fixed amount of 4 units
        if weekNum <= 4:
            self.PlaceOutgoingDelivery(4)  # Fixed delivery amount in the first weeks
        else:
            # After the initial weeks, calculate the delivery based on current stock and orders
            self.PlaceOutgoingDelivery(self.CalcBeerToDeliver())

        # 4. Place an order to the upstream actor (such as a distributor)
        self.PlaceOutgoingOrder(weekNum)

        # 5. Update the wholesaler's costs for the current turn
        self.costsIncurred += self.CalcCostForTurn()
        return

"""# Distributor"""

class Distributor(SupplyChainActor):

    def __init__(self, incomingOrdersQueue, outgoingOrdersQueue, incomingDeliveriesQueue, outgoingDeliveriesQueue):
        # Initialize the distributor with supply chain queues by inheriting from SupplyChainActor
        super().__init__(incomingOrdersQueue, outgoingOrdersQueue, incomingDeliveriesQueue, outgoingDeliveriesQueue)
        return

    def TakeTurn(self, weekNum):
        # Define the steps the distributor performs each turn (weekly):

        # 1. Receive new delivery from the factory
        # This also advances the delivery queue by removing the first item in line
        self.ReceiveIncomingDelivery()

        # 2. Receive new order from the wholesaler
        # This also advances the orders queue by removing the first item in line
        self.ReceiveIncomingOrders()

        # 3. Prepare and place the outgoing delivery to the wholesaler
        # Initially, for the first few weeks, send a fixed amount of 4 units
        if weekNum <= 4:
            self.PlaceOutgoingDelivery(4)  # Fixed delivery amount in the first weeks
        else:
            # After the initial weeks, calculate delivery based on current stock and orders
            self.PlaceOutgoingDelivery(self.CalcBeerToDeliver())

        # 4. Place an order to the upstream actor (e.g., factory) to replenish stock
        self.PlaceOutgoingOrder(weekNum)

        # 5. Update the distributor’s costs for the current turn
        self.costsIncurred += self.CalcCostForTurn()
        return

"""# Factory"""

class Factory(SupplyChainActor):

    def __init__(self, incomingOrdersQueue, outgoingOrdersQueue, incomingDeliveriesQueue, outgoingDeliveriesQueue, productionDelayWeeks):
        # Initialize the factory with supply chain queues and a production delay queue
        super().__init__(incomingOrdersQueue, outgoingOrdersQueue, incomingDeliveriesQueue, outgoingDeliveriesQueue)

        # Initialize a queue to handle production delays (simulating brewing/production time)
        self.BeerProductionDelayQueue = SupplyChainQueue(productionDelayWeeks)

        # Assume the factory has initial production runs in progress for stability
        # These initial production orders help prevent stockouts at the beginning
        self.BeerProductionDelayQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
        self.BeerProductionDelayQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
        return

    def ProduceBeer(self, weekNum):
        # Calculate the amount of beer to produce based on the week number

        if weekNum <= 4:
            amountToOrder = 4  # Fixed initial production amount for the first few weeks
        else:
            # After initial weeks, production amount scales with current orders and target stock
            amountToOrder = 0.5 * self.currentOrders  # Produces enough to cover current orders

            # Adjust production to maintain target stock level if below target
            if (TARGET_STOCK - self.currentStock) > 0:
                amountToOrder += TARGET_STOCK - self.currentStock

        # Add the production order to the production delay queue (simulates delayed production)
        self.BeerProductionDelayQueue.PushEnvelope(amountToOrder)
        self.lastOrderQuantity = amountToOrder  # Track the last production order quantity
        return

    def FinishProduction(self):
        # Complete a production run and add the produced beer to the current stock
        amountProduced = self.BeerProductionDelayQueue.PopEnvelope()

        # Add completed production amount to stock if production is finished
        if amountProduced > 0:
            self.currentStock += amountProduced
        return

    def TakeTurn(self, weekNum):
        # Define the steps the factory performs each turn (weekly):

        # 1. Complete previous production runs (if any) and add to stock
        self.FinishProduction()

        # 2. Receive new orders from the distributor
        # Advances the incoming orders queue by removing the first order
        self.ReceiveIncomingOrders()

        # 3. Prepare and place the outgoing delivery to the distributor
        # Initially, send a fixed amount of 4 units in the first few weeks
        if weekNum <= 4:
            self.PlaceOutgoingDelivery(4)
        else:
            # After initial weeks, calculate delivery based on current stock and orders
            self.PlaceOutgoingDelivery(self.CalcBeerToDeliver())

        # 4. Initiate production to fulfill future demand
        self.ProduceBeer(weekNum)

        # 5. Calculate and update the factory’s costs for the current turn
        self.costsIncurred += self.CalcCostForTurn()
        return

"""# SupplyChainStatistics"""

import plotly.express as px
import plotly.graph_objects as go

class SupplyChainStatistics:

    def __init__(self):
        # Initialize lists to store time-series data for each actor in the supply chain
        # Each list will track metrics over each turn (e.g., week)

        # Costs over time for each supply chain actor
        self.retailerCostsOverTime = []
        self.wholesalerCostsOverTime = []
        self.distributorCostsOverTime = []
        self.factoryCostsOverTime = []

        # Orders over time for each actor
        self.retailerOrdersOverTime = []
        self.wholesalerOrdersOverTime = []
        self.distributorOrdersOverTime = []
        self.factoryOrdersOverTime = []

        # Effective inventory (current stock - current orders) over time for each actor
        self.retailerEffectiveInventoryOverTime = []
        self.wholesalerEffectiveInventoryOverTime = []
        self.distributorEffectiveInventoryOverTime = []
        self.factoryEffectiveInventoryOverTime = []
        return

    # Methods to record orders each week for each actor
    def RecordRetailerOrders(self, retailerOrdersThisWeek):
        self.retailerOrdersOverTime.append(retailerOrdersThisWeek)
        print('Retailer Order:', self.retailerOrdersOverTime[-1])
        return

    def RecordWholesalerOrders(self, wholesalerOrdersThisWeek):
        self.wholesalerOrdersOverTime.append(wholesalerOrdersThisWeek)
        print('Wholesaler Order:', self.wholesalerOrdersOverTime[-1])
        return

    def RecordDistributorOrders(self, distributorOrdersThisWeek):
        self.distributorOrdersOverTime.append(distributorOrdersThisWeek)
        print('Distributor Order:', self.distributorOrdersOverTime[-1])
        return

    def RecordFactoryOrders(self, factoryOrdersThisWeek):
        self.factoryOrdersOverTime.append(factoryOrdersThisWeek)
        print('Factory Order:', self.factoryOrdersOverTime[-1])
        return

    # Methods to record costs incurred each week for each actor
    def RecordRetailerCost(self, retailerCostsThisWeek):
        self.retailerCostsOverTime.append(retailerCostsThisWeek)
        print('Retailer Cost:', self.retailerCostsOverTime[-1])
        return

    def RecordWholesalerCost(self, wholesalerCostsThisWeek):
        self.wholesalerCostsOverTime.append(wholesalerCostsThisWeek)
        print('Wholesaler Cost:', self.wholesalerCostsOverTime[-1])
        return

    def RecordDistributorCost(self, distributorCostsThisWeek):
        self.distributorCostsOverTime.append(distributorCostsThisWeek)
        print('Distributor Cost:', self.distributorCostsOverTime[-1])
        return

    def RecordFactoryCost(self, factoryCostsThisWeek):
        self.factoryCostsOverTime.append(factoryCostsThisWeek)
        print('Factory Cost:', self.factoryCostsOverTime[-1])
        return

    # Methods to record effective inventory each week for each actor
    def RecordRetailerEffectiveInventory(self, retailerEffectiveInventoryThisWeek):
        self.retailerEffectiveInventoryOverTime.append(retailerEffectiveInventoryThisWeek)
        print('Retailer Effective Inventory:', self.retailerEffectiveInventoryOverTime[-1])
        return

    def RecordWholesalerEffectiveInventory(self, wholesalerEffectiveInventoryThisWeek):
        self.wholesalerEffectiveInventoryOverTime.append(wholesalerEffectiveInventoryThisWeek)
        print('Wholesaler Effective Inventory:', self.wholesalerEffectiveInventoryOverTime[-1])
        return

    def RecordDistributorEffectiveInventory(self, distributorEffectiveInventoryThisWeek):
        self.distributorEffectiveInventoryOverTime.append(distributorEffectiveInventoryThisWeek)
        print('Distributor Effective Inventory:', self.distributorEffectiveInventoryOverTime[-1])
        return

    def RecordFactoryEffectiveInventory(self, factoryEffectiveInventoryThisWeek):
        self.factoryEffectiveInventoryOverTime.append(factoryEffectiveInventoryThisWeek)
        print('Factory Effective Inventory:', self.factoryEffectiveInventoryOverTime[-1])
        return

    # Plotting methods to visualize orders, inventory, and costs over time for each actor
    def PlotOrders(self):
        # Create a plot to visualize orders placed over time by each actor
        fig = go.Figure()
        weeks = list(range(0, WEEKS_TO_PLAY + 2))
        fig.add_trace(go.Scatter(x=weeks, y=self.retailerOrdersOverTime, mode='lines+markers',
                    name='Retailer Orders', marker=dict(size=5), marker_color='rgb(215,48,39)'))
        fig.add_trace(go.Scatter(x=weeks, y=self.wholesalerOrdersOverTime, mode='lines+markers',
                    name='Wholesaler Orders', marker=dict(size=5), marker_color='rgb(255,186,0)'))
        fig.add_trace(go.Scatter(x=weeks, y=self.distributorOrdersOverTime, mode='lines+markers',
                    name='Distributor Orders', marker=dict(size=5), marker_color='rgb(126,2,114)'))
        fig.add_trace(go.Scatter(x=weeks, y=self.factoryOrdersOverTime, mode='lines+markers',
                    name='Factory Orders', marker=dict(size=5), marker_color='rgb(69,117,180)'))
        fig.update_layout(title_text='*Orders Placed Over Time*', xaxis_title='Weeks', yaxis_title='Orders',
                          paper_bgcolor='rgba(0,0,0,0)', height=580)
        fig.update_xaxes(range=[0, WEEKS_TO_PLAY])
        fig.show()
        return

    def PlotEffectiveInventory(self):
        # Create a plot to visualize effective inventory over time for each actor
        fig = go.Figure()
        weeks = list(range(0, WEEKS_TO_PLAY + 2))
        fig.add_trace(go.Scatter(x=weeks, y=self.retailerEffectiveInventoryOverTime, mode='lines+markers',
                    name='Retailer Inventory', marker=dict(size=5), marker_color='rgb(215,48,39)'))
        fig.add_trace(go.Scatter(x=weeks, y=self.wholesalerEffectiveInventoryOverTime, mode='lines+markers',
                    name='Wholesaler Inventory', marker=dict(size=5), marker_color='rgb(255,186,0)'))
        fig.add_trace(go.Scatter(x=weeks, y=self.distributorEffectiveInventoryOverTime, mode='lines+markers',
                    name='Distributor Inventory', marker=dict(size=5), marker_color='rgb(126,2,114)'))
        fig.add_trace(go.Scatter(x=weeks, y=self.factoryEffectiveInventoryOverTime, mode='lines+markers',
                    name='Factory Inventory', marker=dict(size=5), marker_color='rgb(69,117,180)'))
        fig.update_layout(title_text='*Effective Inventory Over Time*', xaxis_title='Weeks', yaxis_title='Effective Inventory',
                          paper_bgcolor='rgba(0,0,0,0)', height=580)
        fig.update_xaxes(range=[0, WEEKS_TO_PLAY])
        fig.show()
        return

    def PlotCosts(self):
        # Create a plot to visualize total costs incurred over time by each actor
        fig = go.Figure()
        weeks = list(range(0, WEEKS_TO_PLAY + 2))
        fig.add_trace(go.Scatter(x=weeks, y=self.retailerCostsOverTime, mode='lines+markers',
                    name='Retailer Total Cost', marker=dict(size=5), marker_color='rgb(215,48,39)'))
        fig.add_trace(go.Scatter(x=weeks, y=self.wholesalerCostsOverTime, mode='lines+markers',
                    name='Wholesaler Total Cost', marker=dict(size=5), marker_color='rgb(255,186,0)'))
        fig.add_trace(go.Scatter(x=weeks, y=self.distributorCostsOverTime, mode='lines+markers',
                    name='Distributor Total Cost', marker=dict(size=5), marker_color='rgb(126,2,114)'))
        fig.add_trace(go.Scatter(x=weeks, y=self.factoryCostsOverTime, mode='lines+markers',
                    name='Factory Total Cost', marker=dict(size=5), marker_color='rgb(69,117,180)'))
        fig.update_layout(title_text='*Cost Incurred Over Time*', xaxis_title='Weeks', yaxis_title='Cost ($)',
                          paper_bgcolor='rgba(0,0,0,0)', height=580)
        fig.update_xaxes(range=[0, WEEKS_TO_PLAY])
        fig.show()
        return

"""# Main"""

# Initialize queues between each actor in the supply chain
# Top and bottom queues simulate order (top) and delivery (bottom) flows between actors
wholesalerRetailerTopQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)
wholesalerRetailerBottomQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)

distributorWholesalerTopQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)
distributorWholesalerBottomQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)

factoryDistributorTopQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)
factoryDistributorBottomQueue = SupplyChainQueue(QUEUE_DELAY_WEEKS)

# Populate queues with initial orders to stabilize early weeks of the game
# Each actor's order and delivery queues are initialized with CUSTOMER_INITIAL_ORDERS
for i in range(0, 2):
    wholesalerRetailerTopQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
    wholesalerRetailerBottomQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
    distributorWholesalerTopQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
    distributorWholesalerBottomQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
    factoryDistributorTopQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)
    factoryDistributorBottomQueue.PushEnvelope(CUSTOMER_INITIAL_ORDERS)

# Instantiate the customer
theCustomer = Customer()

# Create Retailer, connected to the customer and wholesaler via queues
myRetailer = Retailer(None, wholesalerRetailerTopQueue, wholesalerRetailerBottomQueue, None, theCustomer)

# Create Wholesaler, connected to the retailer and distributor via queues
myWholesaler = Wholesaler(wholesalerRetailerTopQueue, distributorWholesalerTopQueue,
                          distributorWholesalerBottomQueue, wholesalerRetailerBottomQueue)

# Create Distributor, connected to the wholesaler and factory via queues
myDistributor = Distributor(distributorWholesalerTopQueue, factoryDistributorTopQueue,
                            factoryDistributorBottomQueue, distributorWholesalerBottomQueue)

# Create Factory, connected to the distributor via queues, with a production delay
myFactory = Factory(factoryDistributorTopQueue, None, None, factoryDistributorBottomQueue, QUEUE_DELAY_WEEKS)

# Initialize an object to track and record statistics across the simulation
myStats = SupplyChainStatistics()

# Simulation loop: Iterate over each week
for thisWeek in range(0, WEEKS_TO_PLAY):

    print("\n", "-" * 49)
    print(f" Week {thisWeek}") # Print current week number
    print("-" * 49)

    # Retailer's turn: process orders, calculate costs, and update inventory and statistics
    myRetailer.TakeTurn(thisWeek)
    myStats.RecordRetailerCost(myRetailer.GetCostIncurred())
    myStats.RecordRetailerOrders(myRetailer.GetLastOrderQuantity())
    myStats.RecordRetailerEffectiveInventory(myRetailer.CalcEffectiveInventory())

    # Wholesaler's turn: process orders, calculate costs, and update inventory and statistics
    myWholesaler.TakeTurn(thisWeek)
    myStats.RecordWholesalerCost(myWholesaler.GetCostIncurred())
    myStats.RecordWholesalerOrders(myWholesaler.GetLastOrderQuantity())
    myStats.RecordWholesalerEffectiveInventory(myWholesaler.CalcEffectiveInventory())

    # Distributor's turn: process orders, calculate costs, and update inventory and statistics
    myDistributor.TakeTurn(thisWeek)
    myStats.RecordDistributorCost(myDistributor.GetCostIncurred())
    myStats.RecordDistributorOrders(myDistributor.GetLastOrderQuantity())
    myStats.RecordDistributorEffectiveInventory(myDistributor.CalcEffectiveInventory())

    # Factory's turn: process orders, produce beer, calculate costs, and update statistics
    myFactory.TakeTurn(thisWeek)
    myStats.RecordFactoryCost(myFactory.GetCostIncurred())
    myStats.RecordFactoryOrders(myFactory.GetLastOrderQuantity())
    myStats.RecordFactoryEffectiveInventory(myFactory.CalcEffectiveInventory())

# Output final results after simulation
print("\n--- Final Statistics ----")
print("Beer received by customer: {0}".format(theCustomer.GetBeerReceived()))

# Plot time-series data for orders, inventory, and costs over the weeks of simulation
myStats.PlotOrders()
myStats.PlotEffectiveInventory()
myStats.PlotCosts()