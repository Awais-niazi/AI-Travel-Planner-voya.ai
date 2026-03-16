package handler

import (
	"encoding/json"
	"log/slog"
	"net/http"
	"strconv"

	"github.com/voya/go-services/recommendation/internal/models"
	"github.com/voya/go-services/recommendation/internal/service"
)

type Handler struct {
	svc    *service.RecommendationService
	logger *slog.Logger
}

func NewHandler(svc *service.RecommendationService, logger *slog.Logger) *Handler {
	return &Handler{svc: svc, logger: logger}
}

func (h *Handler) GetRecommendations(w http.ResponseWriter, r *http.Request) {
	var req models.RecommendationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if req.Destination == "" {
		writeError(w, http.StatusBadRequest, "destination is required")
		return
	}

	result := h.svc.GetRecommendations(req)
	writeJSON(w, http.StatusOK, result)
}

func (h *Handler) GetSimilarPlaces(w http.ResponseWriter, r *http.Request) {
	placeID := r.PathValue("place_id")
	if placeID == "" {
		writeError(w, http.StatusBadRequest, "place_id is required")
		return
	}

	limit := 10
	if l := r.URL.Query().Get("limit"); l != "" {
		if parsed, err := strconv.Atoi(l); err == nil && parsed > 0 {
			limit = parsed
		}
	}

	places := h.svc.GetSimilarPlaces(placeID, limit)
	writeJSON(w, http.StatusOK, models.SimilarPlacesResponse{
		PlaceID: placeID,
		Similar: places,
	})
}

func (h *Handler) RecordInteraction(w http.ResponseWriter, r *http.Request) {
	var req models.InteractionRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid request body")
		return
	}

	if err := h.svc.RecordInteraction(req); err != nil {
		h.logger.Error("failed to record interaction", "err", err)
		writeError(w, http.StatusInternalServerError, "failed to record interaction")
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{"status": "recorded"})
}

func (h *Handler) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "recommendation"})
}

// ── Helpers ───────────────────────────────────────────────────────────

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
