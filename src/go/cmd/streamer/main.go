package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/alpacahq/alpaca-trade-api-go/v3/marketdata/stream"
	"github.com/joho/godotenv"
)

func main() {
	if err := godotenv.Load("../../.env"); err != nil {
		log.Println("warning: no .env file found, relying on system environment variables")
	}

	apiKey := os.Getenv("APCA_API_KEY_ID")
	apiSecret := os.Getenv("APCA_API_SECRET_KEY")

	watchlist := []string{"AAPL", "MSFT", "TSLA"}

	client := stream.NewStocksClient(
		"iex",
		stream.WithCredentials(apiKey, apiSecret),
		stream.WithTrades(func(t stream.Trade) {
			fmt.Printf("TRADE  %s  price=%.2f  size=%d  time=%s\n", t.Symbol, t.Price, t.Size, t.Timestamp)
		}, watchlist...),
	)

	ctx := context.Background()
	if err := client.Connect(ctx); err != nil {
		log.Fatalf("failed to connect: %v", err)
	}

	fmt.Println("streamer connected, listening for live trades on:", watchlist)

	if err := <-client.Terminated(); err != nil {
		log.Fatalf("stream terminated with error: %v", err)
	}
}
