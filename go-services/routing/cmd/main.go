package main

import (
	"context"
	"encoding/json"
	"log/slog"
	"math"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

// ── Models ────────────────────────────────────────────────────────────

type Waypoint struct {
	Name      string  `json:"name"`
	Latitude  float64 `json:"lat"`
	Longitude float64 `json:"lng"`
}

type OptimizeRequest struct {
	Waypoints     []Waypoint `json:"waypoints"`
	StartPoint    *Waypoint  `json:"start_point,omitempty"`
	TransportMode string     `json:"transport_mode"` // walking | driving | transit
}

type RouteStep struct {
	From          Waypoint `json:"from"`
	To            Waypoint `json:"to"`
	DistanceKm    float64  `json:"distance_km"`
	DurationMins  int      `json:"duration_mins"`
	TransportMode string   `json:"transport_mode"`
}

type OptimizeResponse struct {
	OrderedWaypoints []Waypoint  `json:"ordered_waypoints"`
	Steps            []RouteStep `json:"steps"`
	TotalDistanceKm  float64     `json:"total_distance_km"`
	TotalDurationMin int         `json:"total_duration_mins"`
}

type DirectionsRequest struct {
	Origin      Waypoint `json:"origin"`
	Destination Waypoint `json:"destination"`
	Mode        string   `json:"mode"`
}

// ── Service ───────────────────────────────────────────────────────────

// optimizeRoute solves TSP using nearest-neighbour heuristic.
// For production, replace with Google Maps Routes API or OSRM.
func optimizeRoute(req OptimizeRequest) OptimizeResponse {
	waypoints := req.Waypoints
	if len(waypoints) == 0 {
		return OptimizeResponse{}
	}

	// Nearest-neighbour TSP: start from first waypoint, greedily pick closest unvisited
	visited := make([]bool, len(waypoints))
	ordered := make([]Waypoint, 0, len(waypoints))
	steps := make([]RouteStep, 0, len(waypoints)-1)

	current := 0
	visited[current] = true
	ordered = append(ordered, waypoints[current])

	for len(ordered) < len(waypoints) {
		nearest := -1
		minDist := math.MaxFloat64

		for i, wp := range waypoints {
			if visited[i] {
				continue
			}
			d := haversine(waypoints[current].Latitude, waypoints[current].Longitude,
				wp.Latitude, wp.Longitude)
			if d < minDist {
				minDist = d
				nearest = i
			}
		}

		if nearest == -1 {
			break
		}

		visited[nearest] = true
		steps = append(steps, RouteStep{
			From:          waypoints[current],
			To:            waypoints[nearest],
			DistanceKm:    math.Round(minDist*100) / 100,
			DurationMins:  estimateDuration(minDist, req.TransportMode),
			TransportMode: req.TransportMode,
		})
		ordered = append(ordered, waypoints[nearest])
		current = nearest
	}

	totalDist := 0.0
	totalMins := 0
	for _, s := range steps {
		totalDist += s.DistanceKm
		totalMins += s.DurationMins
	}

	return OptimizeResponse{
		OrderedWaypoints: ordered,
		Steps:            steps,
		TotalDistanceKm:  math.Round(totalDist*100) / 100,
		TotalDurationMin: totalMins,
	}
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

// estimateDuration converts distance to minutes based on transport mode.
func estimateDuration(distKm float64, mode string) int {
	speeds := map[string]float64{
		"walking": 5.0,  // km/h
		"driving": 40.0, // km/h urban
		"transit": 25.0, // km/h average
	}
	speed, ok := speeds[mode]
	if !ok {
		speed = 5.0
	}
	return int(math.Ceil(distKm / speed * 60))
}

// ── Handlers ──────────────────────────────────────────────────────────

func handleOptimize(w http.ResponseWriter, r *http.Request) {
	var req OptimizeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if req.TransportMode == "" {
		req.TransportMode = "walking"
	}
	result := optimizeRoute(req)
	writeJSON(w, http.StatusOK, result)
}

func handleDirections(w http.ResponseWriter, r *http.Request) {
	var req DirectionsRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	dist := haversine(req.Origin.Latitude, req.Origin.Longitude,
		req.Destination.Latitude, req.Destination.Longitude)
	step := RouteStep{
		From:          req.Origin,
		To:            req.Destination,
		DistanceKm:    math.Round(dist*100) / 100,
		DurationMins:  estimateDuration(dist, req.Mode),
		TransportMode: req.Mode,
	}
	writeJSON(w, http.StatusOK, step)
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "routing"})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// ── Main ──────────────────────────────────────────────────────────────

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8003"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("POST /v1/optimize", handleOptimize)
	mux.HandleFunc("POST /v1/directions", handleDirections)
	mux.HandleFunc("GET /health", handleHealth)

	srv := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		slog.Info("Routing service starting", "port", port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			slog.Error("Server error", "err", err)
			os.Exit(1)
		}
	}()

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	srv.Shutdown(ctx)
	slog.Info("Routing service stopped")
}
