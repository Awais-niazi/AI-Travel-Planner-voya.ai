package service

import (
	"fmt"
	"math"
	"sort"

	"github.com/voya/go-services/itinerary/internal/models"
)

type ItineraryService struct{}

func NewItineraryService() *ItineraryService {
	return &ItineraryService{}
}

func (s *ItineraryService) PlanItinerary(req models.PlanRequest) []models.DayPlan {
	if len(req.Places) == 0 || req.NumDays == 0 {
		return []models.DayPlan{}
	}
	clusters := s.kMeansCluster(req.Places, req.NumDays)
	days := make([]models.DayPlan, 0, req.NumDays)
	for i, cluster := range clusters {
		activities := s.assignTimeSlots(cluster)
		days = append(days, models.DayPlan{
			DayNumber:  i + 1,
			Theme:      s.deriveTheme(i, cluster),
			Date:       fmt.Sprintf("Day %d", i+1),
			Activities: activities,
		})
	}
	return days
}

func (s *ItineraryService) ReplanDay(req models.ReplanRequest) models.DayPlan {
	return models.DayPlan{
		DayNumber: req.DayNumber,
		Theme:     "Updated Day",
		Date:      fmt.Sprintf("Day %d", req.DayNumber),
	}
}

func (s *ItineraryService) kMeansCluster(places []models.Place, k int) [][]models.Place {
	if len(places) <= k {
		clusters := make([][]models.Place, k)
		for i, p := range places {
			clusters[i] = []models.Place{p}
		}
		return clusters
	}
	centroids := make([][2]float64, k)
	step := len(places) / k
	for i := 0; i < k; i++ {
		p := places[i*step]
		centroids[i] = [2]float64{p.Latitude, p.Longitude}
	}
	assignments := make([]int, len(places))
	for iter := 0; iter < 20; iter++ {
		changed := false
		for i, p := range places {
			nearest, minDist := 0, math.MaxFloat64
			for j, c := range centroids {
				if d := haversine(p.Latitude, p.Longitude, c[0], c[1]); d < minDist {
					minDist = d
					nearest = j
				}
			}
			if assignments[i] != nearest {
				assignments[i] = nearest
				changed = true
			}
		}
		if !changed {
			break
		}
		sums := make([][2]float64, k)
		counts := make([]int, k)
		for i, p := range places {
			c := assignments[i]
			sums[c][0] += p.Latitude
			sums[c][1] += p.Longitude
			counts[c]++
		}
		for j := 0; j < k; j++ {
			if counts[j] > 0 {
				centroids[j][0] = sums[j][0] / float64(counts[j])
				centroids[j][1] = sums[j][1] / float64(counts[j])
			}
		}
	}
	clusters := make([][]models.Place, k)
	for i, p := range places {
		clusters[assignments[i]] = append(clusters[assignments[i]], p)
	}
	return clusters
}

func haversine(lat1, lon1, lat2, lon2 float64) float64 {
	const R = 6371.0
	dLat := (lat2 - lat1) * math.Pi / 180
	dLon := (lon2 - lon1) * math.Pi / 180
	a := math.Sin(dLat/2)*math.Sin(dLat/2) +
		math.Cos(lat1*math.Pi/180)*math.Cos(lat2*math.Pi/180)*
			math.Sin(dLon/2)*math.Sin(dLon/2)
	return R * 2 * math.Atan2(math.Sqrt(a), math.Sqrt(1-a))
}

var timeSlots = []string{"9:00 AM", "11:00 AM", "1:00 PM", "3:00 PM", "6:00 PM", "8:00 PM"}

var categoryOrder = map[string]int{
	"attraction": 0,
	"nature":     1,
	"restaurant": 2,
	"experience": 3,
	"shopping":   4,
	"nightlife":  5,
}

func (s *ItineraryService) assignTimeSlots(places []models.Place) []models.Activity {
	sort.Slice(places, func(i, j int) bool {
		oi, ok1 := categoryOrder[places[i].Category]
		oj, ok2 := categoryOrder[places[j].Category]
		if !ok1 {
			oi = 3
		}
		if !ok2 {
			oj = 3
		}
		return oi < oj
	})
	activities := make([]models.Activity, 0, len(places))
	for i, p := range places {
		activities = append(activities, models.Activity{
			Time:          timeSlots[i%len(timeSlots)],
			Name:          p.Name,
			Description:   p.Description,
			Type:          p.Category,
			EstimatedCost: float64(p.PriceLevel) * 15,
			Duration:      s.estimateDuration(p.Category),
			Tags:          p.Tags,
			Latitude:      p.Latitude,
			Longitude:     p.Longitude,
		})
	}
	return activities
}

func (s *ItineraryService) estimateDuration(category string) string {
	switch category {
	case "attraction":
		return "2 hours"
	case "restaurant":
		return "1 hour"
	case "nature":
		return "3 hours"
	case "experience":
		return "2 hours"
	case "nightlife":
		return "3 hours"
	default:
		return "1.5 hours"
	}
}

var dayThemes = []string{
	"Arrival & First Impressions",
	"Deep Culture & History",
	"Hidden Gems & Local Life",
	"Nature & Outdoors",
	"Food, Markets & Neighbourhoods",
	"Art, Design & Architecture",
	"Relaxation & Leisure",
}

func (s *ItineraryService) deriveTheme(dayIndex int, places []models.Place) string {
	if dayIndex == 0 {
		return dayThemes[0]
	}
	counts := make(map[string]int)
	for _, p := range places {
		counts[p.Category]++
	}
	dominant, max := "", 0
	for cat, count := range counts {
		if count > max {
			max = count
			dominant = cat
		}
	}
	switch dominant {
	case "attraction":
		return "Culture & Sightseeing"
	case "nature":
		return "Nature & Outdoors"
	case "restaurant":
		return "Culinary Exploration"
	case "nightlife":
		return "Evening & Nightlife"
	default:
		if dayIndex < len(dayThemes) {
			return dayThemes[dayIndex]
		}
		return fmt.Sprintf("Day %d Exploration", dayIndex+1)
	}
}
