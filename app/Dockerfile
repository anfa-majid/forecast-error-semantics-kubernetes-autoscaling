# syntax=docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e
FROM golang:1.24.6-alpine3.22@sha256:c8c5f95d64aa79b6547f3b626eb84b16a7ce18a139e3e9ca19a8c078b85ba80d AS build
WORKDIR /src
COPY go.mod ./
COPY cmd ./cmd
ARG VERSION=dev
ARG COMMIT=unknown
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w -X main.version=${VERSION} -X main.commit=${COMMIT}" -o /out/benchmark-app ./cmd/benchmark-app

FROM gcr.io/distroless/static-debian12:nonroot@sha256:f5b485ea962d9bd1186b2f6b3a061191539b905b82ec395de78cbfae51f20e35
ARG VERSION=dev
ARG COMMIT=unknown
LABEL org.opencontainers.image.title="Forecast-error autoscaling benchmark application" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${COMMIT}" \
      org.opencontainers.image.source="Forecast-error semantics reproducibility artifact"
COPY --from=build /out/benchmark-app /benchmark-app
EXPOSE 8080
USER 65532:65532
ENTRYPOINT ["/benchmark-app"]
