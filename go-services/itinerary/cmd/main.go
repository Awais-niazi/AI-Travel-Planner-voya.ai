package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/voya/go-services/itinerary/internal/handler"
	"github.com/voya/go-services/itinerary/internal/service"
)

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	slog.SetDefault(logger)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8002"
	}

	svc := service.NewItineraryService()
	h := handler.NewHandler(svc, logger)

	mux := http.NewServeMux()
	mux.HandleFunc("POST /v1/plan", h.PlanItinerary)
	mux.HandleFunc("POST /v1/replan", h.ReplanDay)
	mux.HandleFunc("GET /health", h.Health)

	srv := &http.Server{
		Addr:         ":" + port,
		Handler:      mux,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 20 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	go func() {
		slog.Info("Itinerary service starting", "port", port)
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
	slog.Info("Itinerary service stopped")
}
