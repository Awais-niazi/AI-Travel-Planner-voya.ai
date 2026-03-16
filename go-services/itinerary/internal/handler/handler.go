package handler

import (
	"encoding/json"
	"log/slog"
	"net/http"

	"github.com/voya/go-services/itinerary/internal/models"
	"github.com/voya/go-services/itinerary/internal/service"
)

type Handler struct {
	svc    *service.ItineraryService
	logger *slog.Logger
}

func NewHandler(svc *service.ItineraryService, logger *slog.Logger) *Handler {
	return &Handler{svc: svc, logger: logger}
}

func (h *Handler) PlanItinerary(w http.ResponseWriter, r *http.Request) {
	var req models.PlanRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}
	if req.NumDays <= 0 {
		writeError(w, http.StatusBadRequest, "num_days must be greater than 0")
		return
	}

	days := h.svc.PlanItinerary(req)
	writeJSON(w, http.StatusOK, days)
}

func (h *Handler) ReplanDay(w http.ResponseWriter, r *http.Request) {
	var req models.ReplanRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	day := h.svc.ReplanDay(req)
	writeJSON(w, http.StatusOK, day)
}

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "itinerary"})
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
