package service

import (
	"math"
	"sort"
	"strings"

	"github.com/voya/go-services/recommendation/internal/models"
)

type RecommendationService struct{}

func NewRecommendationService() *RecommendationService {
	return &RecommendationService{}
}

func (s *RecommendationService) GetRecommendations(req models.RecommendationRequest) models.RecommendationResponse {
	candidates := s.fetchCandidates(req.Destination)
	filtered := s.filterByBudget(candidates, req.BudgetLevel)
	scored := s.scoreByInterests(filtered, req.Interests)
	sorted := s.sortByScore(scored)
	if len(sorted) > 50 {
		sorted = sorted[:50]
	}
	return models.RecommendationResponse{
		Destination: req.Destination,
		Places:      sorted,
		TotalCount:  len(sorted),
	}
}

func (s *RecommendationService) GetSimilarPlaces(_ string, _ int) []models.Place {
	return []models.Place{}
}

func (s *RecommendationService) RecordInteraction(req models.InteractionRequest) error {
	return nil
}

func (s *RecommendationService) fetchCandidates(_ string) []models.Place {
	return []models.Place{
		{ID: "p1", Name: "Historic Old Town", Description: "The cultural heart of the city with centuries-old architecture.", Category: "attraction", Rating: 4.7, PriceLevel: 1, Tags: []string{"culture", "history", "architecture"}},
		{ID: "p2", Name: "Central Food Market", Description: "Bustling covered market selling local produce, street food, and crafts.", Category: "restaurant", Rating: 4.5, PriceLevel: 2, Tags: []string{"food", "local", "market"}},
		{ID: "p3", Name: "National Museum", Description: "World-class collection spanning art, history, and natural sciences.", Category: "attraction", Rating: 4.6, PriceLevel: 2, Tags: []string{"art", "history", "culture"}},
		{ID: "p4", Name: "Riverside Park", Description: "Scenic waterfront park ideal for walks, cycling, and picnics.", Category: "nature", Rating: 4.4, PriceLevel: 1, Tags: []string{"nature", "outdoor", "walking"}},
		{ID: "p5", Name: "Rooftop Bar District", Description: "A cluster of rooftop bars with panoramic city views.", Category: "nightlife", Rating: 4.3, PriceLevel: 3, Tags: []string{"nightlife", "drinks", "views"}},
		{ID: "p6", Name: "Luxury Spa & Wellness", Description: "Award-winning spa offering traditional treatments and modern therapies.", Category: "wellness", Rating: 4.8, PriceLevel: 4, Tags: []string{"wellness", "spa", "luxury"}},
	}
}

func (s *RecommendationService) filterByBudget(places []models.Place, budgetLevel string) []models.Place {
	maxPrice := map[string]int{"budget": 2, "mid": 3, "luxury": 4}
	max, ok := maxPrice[budgetLevel]
	if !ok {
		max = 4
	}
	out := make([]models.Place, 0, len(places))
	for _, p := range places {
		if p.PriceLevel <= max {
			out = append(out, p)
		}
	}
	return out
}

func (s *RecommendationService) scoreByInterests(places []models.Place, interests []string) []models.Place {
	if len(interests) == 0 {
		for i := range places {
			places[i].Score = places[i].Rating / 5.0
		}
		return places
	}
	interestSet := make(map[string]bool, len(interests))
	for _, interest := range interests {
		interestSet[strings.ToLower(interest)] = true
	}
	for i, p := range places {
		overlap := 0
		for _, tag := range p.Tags {
			if interestSet[strings.ToLower(tag)] {
				overlap++
			}
		}
		relevance := float64(overlap) / float64(len(interests))
		places[i].Score = math.Round((relevance*0.6+p.Rating/5.0*0.4)*100) / 100
	}
	return places
}

func (s *RecommendationService) sortByScore(places []models.Place) []models.Place {
	sort.Slice(places, func(i, j int) bool {
		return places[i].Score > places[j].Score
	})
	return places
}
