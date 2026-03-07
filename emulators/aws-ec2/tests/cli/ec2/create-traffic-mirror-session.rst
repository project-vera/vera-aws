**Example 1: To create a traffic mirror session with a packet length limit**

The following ``create-traffic-mirror-session`` example creates a traffic mirror session that captures only the first 25 bytes of each packet. Use ``--packet-length`` when you only need packet headers for analysis and want to reduce the volume of mirrored traffic. ::

    aws ec2 create-traffic-mirror-session \
        --description 'example session' \
        --traffic-mirror-target-id tmt-07f75d8feeEXAMPLE \
        --network-interface-id eni-070203f901EXAMPLE \
        --session-number 1 \
        --packet-length 25 \
        --traffic-mirror-filter-id tmf-04812ff784EXAMPLE

Output::

    {
        "TrafficMirrorSession": {
            "TrafficMirrorSessionId": "tms-08a33b1214EXAMPLE",
            "TrafficMirrorTargetId": "tmt-07f75d8feeEXAMPLE",
            "TrafficMirrorFilterId": "tmf-04812ff784EXAMPLE",
            "NetworkInterfaceId": "eni-070203f901EXAMPLE",
            "OwnerId": "111122223333",
            "PacketLength": 25,
            "SessionNumber": 1,
            "VirtualNetworkId": 7159709,
            "Description": "example session",
            "Tags": []
        },
        "ClientToken": "5236cffc-ee13-4a32-bb5b-388d9da09d96"
    }

For more information, see `Create a traffic mirror session <https://docs.aws.amazon.com/vpc/latest/mirroring/create-traffic-mirroring-session.html>`__ in the *Traffic Mirroring Guide*.

**Example 2: To create a traffic mirror session that captures full packets**

The following ``create-traffic-mirror-session`` example creates a traffic mirror session without a packet length limit, so that complete packets are mirrored to the target. Omitting ``--packet-length`` is appropriate when you need full payload inspection, such as for deep packet analysis or application-layer monitoring. Note that ``PacketLength`` is absent from the output. ::

    aws ec2 create-traffic-mirror-session \
        --description 'full packet session' \
        --traffic-mirror-target-id tmt-07f75d8feeEXAMPLE \
        --network-interface-id eni-070203f901EXAMPLE \
        --session-number 2 \
        --traffic-mirror-filter-id tmf-04812ff784EXAMPLE

Output::

    {
        "TrafficMirrorSession": {
            "TrafficMirrorSessionId": "tms-09b44c1325EXAMPLE",
            "TrafficMirrorTargetId": "tmt-07f75d8feeEXAMPLE",
            "TrafficMirrorFilterId": "tmf-04812ff784EXAMPLE",
            "NetworkInterfaceId": "eni-070203f901EXAMPLE",
            "OwnerId": "111122223333",
            "SessionNumber": 2,
            "VirtualNetworkId": 8260810,
            "Description": "full packet session",
            "Tags": []
        },
        "ClientToken": "7a48e6b1-cc24-5d43-ca6c-499e1eb0d87a"
    }

For more information, see `Create a traffic mirror session <https://docs.aws.amazon.com/vpc/latest/mirroring/create-traffic-mirroring-session.html>`__ in the *Traffic Mirroring Guide*.
