package service

// RecommendationRequest is the payload from the FastAPI layer.
type RecommendationRequest struct {
	Destination string   `json:"destination"`
	Interests   []string `json:"interests"`
	BudgetLevel string   `json:"budget_level"` // budget | mid | luxury
	TravelStyle string   `json:"travel_style"`
	UserID      *string  `json:"user_id,omitempty"`
}

// Place represents a recommended attraction, restaurant, or experience.
type Place struct {
	ID          string   `json:"id"`
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Category    string   `json:"category"` // attraction | restaurant | hotel | experience
	Latitude    float64  `json:"latitude"`
	Longitude   float64  `json:"longitude"`
	Address     string   `json:"address"`
	Rating      float64  `json:"rating"`
	PriceLevel  int      `json:"price_level"` // 1–4
	Tags        []string `json:"tags"`
	Score       float64  `json:"score"` // recommendation score 0–1
}

// RecommendationResponse is the ranked list returned to FastAPI.
type RecommendationResponse struct {
	Destination string  `json:"destination"`
	Places      []Place `json:"places"`
	TotalCount  int     `json:"total_count"`
}

// InteractionRequest records a user behaviour event.
type InteractionRequest struct {
	UserID          string `json:"user_id"`
	PlaceID         string `json:"place_id"`
	InteractionType string `json:"type"` // view | save | complete
}

// SimilarPlacesResponse wraps content-based similarity results.
type SimilarPlacesResponse struct {
	PlaceID string  `json:"place_id"`
	Similar []Place `json:"similar"`
}
