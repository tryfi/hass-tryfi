# Working TryFi GraphQL Queries

Based on the exploration, here are the GraphQL queries that successfully work with the TryFi API:

## 1. Get User Details
```graphql
query {
  currentUser {
    ...UserDetails
  }
}

fragment UserDetails on User {
  __typename
  id
  email
  firstName
  lastName
  phoneNumber
  fiNewsNotificationsEnabled
  chipReseller {
    __typename
    id
  }
}
```

## 2. Get Full Household Data (Pets & Bases)
```graphql
query {
  currentUser {
    ...UserFullDetails
  }
}

# Includes all the fragments for complete data
```

## 3. Get Pet Current Location
```graphql
query {
  pet(id: "PET_ID") {
    ongoingActivity {
      __typename
      ...OngoingActivityDetails
    }
  }
}
```

## 4. Get Pet Activity Stats
```graphql
query {
  pet(id: "PET_ID") {
    dailyStat: currentActivitySummary(period: DAILY) {
      ...ActivitySummaryDetails
    }
    weeklyStat: currentActivitySummary(period: WEEKLY) {
      ...ActivitySummaryDetails
    }
    monthlyStat: currentActivitySummary(period: MONTHLY) {
      ...ActivitySummaryDetails
    }
  }
}
```

## 5. Get Pet Rest Stats
```graphql
query {
  pet(id: "PET_ID") {
    dailyStat: restSummaryFeed(cursor: null, period: DAILY, limit: 1) {
      __typename
      restSummaries {
        __typename
        ...RestSummaryDetails
      }
    }
    weeklyStat: restSummaryFeed(cursor: null, period: WEEKLY, limit: 1) {
      __typename
      restSummaries {
        __typename
        ...RestSummaryDetails
      }
    }
    monthlyStat: restSummaryFeed(cursor: null, period: MONTHLY, limit: 1) {
      __typename
      restSummaries {
        __typename
        ...RestSummaryDetails
      }
    }
  }
}
```

## 6. Get Device Details
```graphql
query {
  pet(id: "PET_ID") {
    __typename
    ...PetProfile
  }
}
```

## Available Mutations

### 1. Update Device Operation Parameters
```graphql
mutation UpdateDeviceOperationParams($input: UpdateDeviceOperationParamsInput!) {
  updateDeviceOperationParams(input: $input) {
    __typename
    ...DeviceDetails
  }
}
```
Used for:
- Setting lost dog mode (mode: "LOST_DOG" or "NORMAL")
- Turning LED on/off (ledEnabled: true/false)

### 2. Set Device LED Color
```graphql
mutation SetDeviceLed($moduleId: String!, $ledColorCode: Int!) {
  setDeviceLed(moduleId: $moduleId, ledColorCode: $ledColorCode) {
    __typename
    ...DeviceDetails
  }
}
```
Color codes: 2=Red, 3=Green, 4=Blue, 5=Purple, 6=Yellow, 7=Cyan, 8=White

## Data Structure Notes

### Device Info Contains:
- `batteryPercent`: Current battery level
- `bq27421Info`: Detailed battery information including health, temperature, capacity
- `manifest`: Firmware versions for all components
- `wifiNetworkNames`: List of configured WiFi networks
- `wifiStats`: Connection statistics per network
- `bleConnectionStats`: Bluetooth connection quality data
- `deviceStats`: Extensive usage statistics
- `lleStatus`: GPS/GLONASS/Galileo validity dates

### OngoingActivity Contains:
- `__typename`: "OngoingWalk" or "OngoingRest"
- `start`: Activity start time
- `areaName`: Current area name
- `position` (for rest) or `positions` (for walk): GPS coordinates
- `place`: Place details when resting (name, address)
- `distance`, `steps`: For walks only

### RestSummary Contains:
- `start`, `end`: Time period
- `data.sleepAmounts`: Array with type ("SLEEP" or "NAP") and duration

## Authentication
- Login endpoint: `POST https://api.tryfi.com/auth/login`
- Parameters: `email`, `password`
- Returns: `userId`, `sessionId`
- Session management handled via requests.Session()