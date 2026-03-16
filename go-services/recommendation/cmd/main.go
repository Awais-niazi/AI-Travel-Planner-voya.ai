package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/voya/go-services/recommendation/internal/handler"
	"github.com/voya/go-services/recommendation/internal/service"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8001"
	}

	svc := service.NewRecommendationService()
	h := handler.NewHandler(svc, logger)

	mux := http.NewServeMux()
	mux.HandleFunc("POST /v1/recommendations", h.GetRecommendations)
	mux.HandleFunc("GET /v1/places/{place_id}/similar", h.GetSimilarPlaces)
	mux.HandleFunc("POST /v1/interactions", h.RecordInteraction)
	mux.HandleFunc("GET /health", h.Health)

	srv := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		slog.Info("Recommendation service starting", "port", port)
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
	if err := srv.Shutdown(ctx); err != nil {
		slog.Error("Shutdown error", "err", err)
	}
	slog.Info("Recommendation service stopped")
}
