# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM golang:1.24.6-alpine3.22@sha256:c8c5f95d64aa79b6547f3b626eb84b16a7ce18a139e3e9ca19a8c078b85ba80d AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
ARG VERSION=1.1.2
ARG COMMIT=unknown
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go test ./... -count=1 && \
    CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -ldflags="-s -w -X main.version=${VERSION} -X main.commit=${COMMIT}" -o /out/predictive-autoscaler ./cmd/predictive-autoscaler

FROM gcr.io/distroless/static-debian12:nonroot@sha256:f5b485ea962d9bd1186b2f6b3a061191539b905b82ec395de78cbfae51f20e35
LABEL org.opencontainers.image.title="Predictive Autoscaler with Reactive Safety Net" \
      org.opencontainers.image.version="1.1.2" \
      org.opencontainers.image.source="Forecast-error semantics reproducibility artifact"
COPY --from=build /out/predictive-autoscaler /predictive-autoscaler
USER 65532:65532
ENTRYPOINT ["/predictive-autoscaler"]
