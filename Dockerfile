FROM maven:3.8-jdk-8 as maven_builder

COPY src /src/
COPY pom.xml .

RUN mvn clean package

FROM tomcat:jdk8

COPY --from=maven_builder /target/rdfconv.war /usr/local/tomcat/webapps

CMD ["catalina.sh", "run"]
