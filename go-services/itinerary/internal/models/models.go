package models

// PlanRequest is sent by FastAPI with ranked places to schedule.
type PlanRequest struct {
	Destination string  `json:"destination"`
	NumDays     int     `json:"num_days"`
	Places      []Place `json:"places"`
	BudgetLevel string  `json:"budget_level"`
	TravelStyle string  `json:"travel_style"`
}

// Place is a recommended location to include in the itinerary.
type Place struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Category    string   `json:"category"`
	Latitude    float64  `json:"latitude"`
	Longitude   float64  `json:"longitude"`
	PriceLevel  int      `json:"price_level"`
	Tags        []string `json:"tags"`
	Score       float64  `json:"score"`
}

// Activity is a scheduled time slot within a day.
type Activity struct {
	Time          string   `json:"time"`
	Name          string   `json:"name"`
	Description   string   `json:"description"`
	Type          string   `json:"type"`
	EstimatedCost float64  `json:"estimatedCost"`
	Duration      string   `json:"duration"`
	Tags          []string `json:"tags"`
	Latitude      float64  `json:"latitude,omitempty"`
	Longitude     float64  `json:"longitude,omitempty"`
}

// DayPlan is the output for a single day.
type DayPlan struct {
	DayNumber  int        `json:"dayNumber"`
	Theme      string     `json:"theme"`
	Date       string     `json:"date"`
	Activities []Activity `json:"activities"`
}

// ReplanRequest asks the service to rebuild a single day.
type ReplanRequest struct {
	TripID      string         `json:"trip_id"`
	DayNumber   int            `json:"day_number"`
	Constraints map[string]any `json:"constraints"`
}
